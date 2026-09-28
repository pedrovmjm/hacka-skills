import { useEffect, useMemo, useState } from "react";

const API_URL = "http://localhost:8001";
const GOAL = 8;
const USERS = { ana: { name: "Ana", role: "Gestora" }, bruno: { name: "Bruno", role: "Colaborador" } };
const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const monthLabel = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" });
const dateLabel = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
const pad = (value) => String(value).padStart(2, "0");
const toMonth = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
const toDate = (year, month, day) => `${year}-${pad(month + 1)}-${pad(day)}`;
const parseDate = (value) => { const [y, m, d] = value.split("-").map(Number); return new Date(y, m - 1, d); };

function normalizeDays(days = []) {
  if (Array.isArray(days)) return days;
  return Object.entries(days).map(([attendance_date, value]) => typeof value === "string" ? { attendance_date, status: value } : { attendance_date, ...value });
}

function calendarCells(reference) {
  const year = reference.getFullYear();
  const month = reference.getMonth();
  const offset = new Date(year, month, 1).getDay();
  const length = new Date(year, month + 1, 0).getDate();
  return [...Array.from({ length: offset }, (_, i) => ({ key: `blank-${i}` })), ...Array.from({ length }, (_, i) => ({ key: toDate(year, month, i + 1), attendance_date: toDate(year, month, i + 1), day: i + 1 }))];
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    let message = "Não foi possível concluir a solicitação.";
    try { const body = await response.json(); message = body.detail || body.message || message; } catch { /* resposta sem JSON */ }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

function Icon({ name }) {
  const paths = {
    left: <path d="m15 18-6-6 6-6" />, right: <path d="m9 18 6-6-6-6" />, check: <path d="m5 12 4 4L19 6" />,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function MonthNav({ month, onChange }) {
  const move = (amount) => onChange(new Date(month.getFullYear(), month.getMonth() + amount, 1));
  return <div className="month-nav" aria-label="Navegação de mês"><button onClick={() => move(-1)} aria-label="Mês anterior"><Icon name="left"/></button><h2>{monthLabel.format(month)}</h2><button onClick={() => move(1)} aria-label="Próximo mês"><Icon name="right"/></button></div>;
}

function Progress({ value, label }) {
  const percent = Math.min(Math.max(value || 0, 0), 100);
  return <div className="progress" aria-label={label}><div><span style={{ width: `${percent}%` }}/></div><small>{Math.round(value || 0)}%</small></div>;
}

function Calendar({ month, days, selected, onSelect, readOnly }) {
  const map = useMemo(() => new Map(normalizeDays(days).map((day) => [day.attendance_date, day])), [days]);
  const cells = useMemo(() => calendarCells(month), [month]);
  const now = new Date();
  const today = toMonth(now) === toMonth(month) ? toDate(now.getFullYear(), now.getMonth(), now.getDate()) : "";
  return <div className={`calendar ${readOnly ? "read-only" : ""}`}>
    <div className="weekdays" aria-hidden="true">{WEEKDAYS.map((day) => <span key={day}>{day}</span>)}</div>
    <div className="calendar-grid" role="grid" aria-label={`Calendário de ${monthLabel.format(month)}`}>{cells.map((cell) => {
      if (!cell.attendance_date) return <span className="blank" key={cell.key}/>;
      const item = map.get(cell.attendance_date); const status = item?.status;
      const state = status === "present" ? "fui ao polo" : status === "absent" ? "não fui" : "sem marcação";
      return <button key={cell.key} role="gridcell" className={`day ${status || "unmarked"} ${selected === cell.attendance_date ? "selected" : ""} ${today === cell.attendance_date ? "today" : ""}`} onClick={() => onSelect?.(cell.attendance_date)} aria-label={`${cell.day} de ${monthLabel.format(month)}, ${state}`} aria-selected={selected === cell.attendance_date}>
        <strong>{cell.day}</strong>{status && <small>{status === "present" ? "Presente" : "Ausente"}</small>}{item?.notes && <i title="Possui observação"/>}
      </button>;
    })}</div>
  </div>;
}

function Editor({ date, item, saving, onSave, onDelete, onClose }) {
  const [status, setStatus] = useState(item?.status || "present");
  const [notes, setNotes] = useState(item?.notes || "");
  useEffect(() => { setStatus(item?.status || "present"); setNotes(item?.notes || ""); }, [date, item]);
  return <aside className="editor" aria-labelledby="editor-title">
    <div className="editor-head"><div><p className="eyebrow">Editar dia</p><h3 id="editor-title">{dateLabel.format(parseDate(date))}</h3></div><button className="close" onClick={onClose} aria-label="Fechar editor">×</button></div>
    <fieldset><legend>Como foi seu dia?</legend>{[["present", "Fui ao polo", "Conta para sua meta mensal"], ["absent", "Não fui", "Registra ausência neste dia"]].map(([value, title, subtitle]) => <label className={`status ${status === value ? "active" : ""}`} key={value}><input type="radio" name="status" value={value} checked={status === value} onChange={(e) => setStatus(e.target.value)}/><b className={value}>{value === "present" ? <Icon name="check"/> : "—"}</b><span><strong>{title}</strong><small>{subtitle}</small></span></label>)}</fieldset>
    <label className="notes">Observação <small>opcional</small><textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows="3" placeholder="Ex.: reunião com o time"/>{item?.notes && <span className="notes-preview"><small>Observação salva</small><span dangerouslySetInnerHTML={{ __html: item.notes }}/></span>}</label>
    <div className="editor-actions"><button className="primary" disabled={saving} onClick={() => onSave(status, notes)}>{saving ? "Salvando..." : "Salvar marcação"}</button>{item && <button className="delete" disabled={saving} onClick={onDelete}>Limpar marcação</button>}</div>
  </aside>;
}

function Personal({ data, month, selected, setSelected, loading, saving, onSave, onDelete }) {
  const days = normalizeDays(data?.days); const item = days.find((day) => day.attendance_date === selected);
  const goal = Number(data?.goal ?? GOAL); const present = Number(data?.present_count ?? 0); const absent = Number(data?.absent_count ?? 0);
  const remaining = Number(data?.remaining_count ?? Math.max(goal - present, 0)); const percent = Number(data?.progress_percent ?? Math.round(present / goal * 100));
  return <div className="personal-layout">
    <section className="card calendar-card"><div className="card-head"><div><p className="eyebrow">Seu mês</p><h2>Calendário de presença</h2></div><div className="legend"><span><i className="present"/> Presente</span><span><i className="absent"/> Não fui</span></div></div>{loading ? <div className="skeleton" aria-label="Carregando calendário"/> : <Calendar month={month} days={days} selected={selected} onSelect={setSelected}/>}</section>
    <aside className="side"><section className="goal"><p className="eyebrow">Meta mensal</p><div><strong>{present}</strong><span>de {goal} dias</span></div><Progress value={percent} label={`${percent}% da meta mensal`}/><p>{remaining ? <><b>Faltam {remaining} dias</b> para alcançar sua meta.</> : <><b>Meta alcançada!</b> Continue assim.</>}</p><small>{absent} {absent === 1 ? "ausência marcada" : "ausências marcadas"}</small></section><section className="tip"><span>💡</span><div><b>Organize sua rotina</b><p>Clique em um dia para registrar ou corrigir sua presença.</p></div></section></aside>
    {selected && <Editor key={selected} date={selected} item={item} saving={saving} onSave={onSave} onDelete={onDelete} onClose={() => setSelected("")}/>}
  </div>;
}

function memberFrom(raw, index) {
  const present = Number(raw.present_count ?? raw.present ?? raw.days_present ?? 0); const goal = Number(raw.goal ?? GOAL);
  return { id: raw.user_id ?? raw.id ?? `member-${index}`, name: raw.name ?? raw.user_name ?? raw.display_name ?? raw.user_id ?? `Pessoa ${index + 1}`, present, goal, remaining: Number(raw.remaining_count ?? Math.max(goal - present, 0)), percent: Number(raw.progress_percent ?? Math.round(present / goal * 100)), days: normalizeDays(raw.days) };
}

function Team({ data, month, loading, selected, setSelected }) {
  if (loading) return <div className="card skeleton team-loading" aria-label="Carregando visão do time"/>;
  const members = (data?.members ?? data?.people ?? data?.team ?? []).map(memberFrom);
  const active = members.find((person) => person.id === selected);
  const total = Number(data?.team_present_total ?? data?.total_present ?? data?.present_count ?? members.reduce((sum, person) => sum + person.present, 0));
  const average = Number(data?.team_average ?? data?.average_present ?? data?.average ?? (members.length ? total / members.length : 0));
  return <div className="team-view">
    <section className="team-summary">{[["users", "Tamanho do time", data?.team_size ?? members.length, "pessoas"], ["calendar", "Total de presenças", total, "dias no mês"], ["check", "Média por pessoa", average.toFixed(1).replace(".", ","), `de ${data?.goal ?? GOAL} dias`]].map(([icon, label, value, suffix]) => <article key={label}><b><Icon name={icon}/></b><div><small>{label}</small><strong>{value}</strong><span>{suffix}</span></div></article>)}</section>
    <section className="card team-card"><div className="card-head"><div><p className="eyebrow">Acompanhamento</p><h2>Presença do time</h2><p>Selecione uma pessoa para consultar os dias marcados.</p></div><span className="chip">Meta: {data?.goal ?? GOAL} dias</span></div>{members.length === 0 ? <p className="empty">Nenhum integrante encontrado para este mês.</p> : <div className="members">{members.map((person) => <button className={`member ${selected === person.id ? "active" : ""}`} key={person.id} onClick={() => setSelected(selected === person.id ? "" : person.id)} aria-expanded={selected === person.id}><span className="avatar">{person.name.slice(0, 2).toUpperCase()}</span><span className="member-name"><b>{person.name}</b><small>{person.present >= person.goal ? "Meta alcançada" : `${person.remaining} dias restantes`}</small></span><span className="member-progress"><Progress value={person.percent} label={`${person.name}: ${person.percent}% da meta`}/></span><span className="member-count"><b>{person.present}</b><small>de {person.goal} dias</small></span><Icon name="right"/></button>)}</div>}</section>
    {active && <section className="card detail"><div className="card-head"><div><p className="eyebrow">Detalhe mensal</p><h2>Calendário de {active.name}</h2></div><button className="close" onClick={() => setSelected("")} aria-label="Fechar detalhe">×</button></div><div className="legend"><span><i className="present"/> Presente</span><span><i className="absent"/> Não foi</span></div><Calendar month={month} days={active.days} readOnly/>{active.days.some((day) => day.notes) && <div className="team-notes"><h3>Observações do mês</h3>{active.days.filter((day) => day.notes).map((day) => <article key={day.attendance_date}><time>{dateLabel.format(parseDate(day.attendance_date))}</time><div dangerouslySetInnerHTML={{ __html: day.notes }}/></article>)}</div>}</section>}
  </div>;
}

export default function App() {
  const [user, setUser] = useState("ana"); const [tab, setTab] = useState("personal");
  const [month, setMonth] = useState(() => { const now = new Date(); return new Date(now.getFullYear(), now.getMonth(), 1); });
  const [attendance, setAttendance] = useState(null); const [team, setTeam] = useState(null);
  const [selectedDate, setSelectedDate] = useState(""); const [selectedMember, setSelectedMember] = useState("");
  const [loading, setLoading] = useState(true); const [saving, setSaving] = useState(false); const [notice, setNotice] = useState(null);
  const currentMonth = toMonth(month);

  async function load() {
    setLoading(true); setNotice(null);
    try { const headers = { "X-User": user }; if (tab === "personal") setAttendance(await request(`/api/attendance?user_id=${encodeURIComponent(user)}&month=${currentMonth}`, { headers })); else setTeam(await request(`/api/team-attendance?manager_id=${encodeURIComponent(user)}&month=${currentMonth}`, { headers })); }
    catch (error) { setNotice({ type: "error", text: error.message }); } finally { setLoading(false); }
  }
  useEffect(() => { setSelectedDate(""); setSelectedMember(""); load(); }, [user, tab, currentMonth]);

  async function save(status, notes) {
    setSaving(true); setNotice(null);
    try { await request(`/api/attendance/${selectedDate}`, { method: "PUT", headers: { "Content-Type": "application/json", "X-User": user }, body: JSON.stringify({ user_id: user, status, notes }) }); setSelectedDate(""); await load(); setNotice({ type: "success", text: "Marcação salva com sucesso." }); }
    catch (error) { setNotice({ type: "error", text: error.message }); } finally { setSaving(false); }
  }
  async function remove() {
    setSaving(true); setNotice(null);
    try { await request(`/api/attendance/${selectedDate}?user_id=${encodeURIComponent(user)}`, { method: "DELETE", headers: { "X-User": user } }); setSelectedDate(""); await load(); setNotice({ type: "success", text: "Marcação removida." }); }
    catch (error) { setNotice({ type: "error", text: error.message }); } finally { setSaving(false); }
  }

  return <div className="app-shell">
    <header className="topbar"><div className="brand"><span aria-label="Itaú">Itaú</span><div><b>Presença no polo</b><small>Controle de dias presenciais</small></div></div><label className="profile"><span>Perfil</span><select value={user} onChange={(e) => setUser(e.target.value)} aria-label="Perfil fictício">{Object.entries(USERS).map(([id, profile]) => <option key={id} value={id}>{profile.name} · {profile.role}</option>)}</select></label></header>
    <div className="demo" role="note"><span>i</span><b>Projeto demonstrativo, sem vínculo com o Itaú.</b></div>
    <main className="page"><section className="welcome"><div><p className="eyebrow">Olá, {USERS[user].name}</p><h1>Acompanhe sua presença no polo</h1><p>Registre seus dias presenciais e mantenha sua meta mensal em dia.</p></div><MonthNav month={month} onChange={setMonth}/></section>
      <nav className="tabs" aria-label="Áreas de presença"><button className={tab === "personal" ? "active" : ""} onClick={() => setTab("personal")} aria-current={tab === "personal" ? "page" : undefined}><Icon name="calendar"/>Minha presença</button><button className={tab === "team" ? "active" : ""} onClick={() => setTab("team")} aria-current={tab === "team" ? "page" : undefined}><Icon name="users"/>Visão do time</button></nav>
      {notice && <div className={`notice ${notice.type}`} role={notice.type === "error" ? "alert" : "status"}><b>{notice.type === "success" ? "✓" : "!"}</b>{notice.text}<button onClick={() => setNotice(null)} aria-label="Fechar mensagem">×</button></div>}
      {tab === "personal" ? <Personal data={attendance} month={month} selected={selectedDate} setSelected={setSelectedDate} loading={loading} saving={saving} onSave={save} onDelete={remove}/> : <Team data={team} month={month} loading={loading} selected={selectedMember} setSelected={setSelectedMember}/>}
    </main><footer><span>Presença no polo</span><span>Ambiente fictício para fins demonstrativos</span></footer>
  </div>;
}
