import { useEffect, useState } from "react";

const API = "http://localhost:8001";
const emptyForm = {
  visitor_name: "",
  visit_date: "",
  start_time: "",
  purpose: "",
  notes: "",
  companions: 0,
  status: "scheduled",
};

export default function App() {
  const [user, setUser] = useState("ana");
  const [visits, setVisits] = useState([]);
  const [summary, setSummary] = useState({ scheduled: 0, completed: 0, cancelled: 0, total: 0 });
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadEverything(selectedUser = user, search = query) {
    setLoading(true);
    try {
      const headers = { "X-User": selectedUser };
      const [visitResponse, summaryResponse] = await Promise.all([
        fetch(`${API}/api/visits?user_id=${selectedUser}&q=${encodeURIComponent(search)}`, { headers }),
        fetch(`${API}/api/summary?user_id=${selectedUser}`, { headers }),
      ]);
      if (!visitResponse.ok || !summaryResponse.ok) throw new Error("Nao foi possivel carregar os dados");
      setVisits(await visitResponse.json());
      setSummary(await summaryResponse.json());
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEverything(user, "");
  }, [user]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm({ ...form, [name]: name === "companions" ? Number(value) : value });
  }

  async function saveVisit(event) {
    event.preventDefault();
    setMessage("");
    if (!form.visitor_name || !form.visit_date || !form.start_time || !form.purpose) {
      setMessage("Preencha nome, data, horario e finalidade.");
      return;
    }
    const url = editingId ? `${API}/api/visits/${editingId}` : `${API}/api/visits`;
    const payload = editingId ? form : { ...form, user_id: user };
    try {
      const response = await fetch(url, {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", "X-User": user },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || "Falha ao salvar");
      }
      setForm(emptyForm);
      setEditingId(null);
      setMessage(editingId ? "Agendamento atualizado." : "Ida agendada.");
      await loadEverything();
    } catch (error) {
      setMessage(error.message);
    }
  }

  function startEditing(visit) {
    setEditingId(visit.id);
    setForm({
      visitor_name: visit.visitor_name,
      visit_date: visit.visit_date,
      start_time: visit.start_time,
      purpose: visit.purpose,
      notes: visit.notes,
      companions: visit.companions,
      status: visit.status,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function cancelVisit(id) {
    if (!window.confirm("Cancelar esta ida ao polo?")) return;
    try {
      const response = await fetch(`${API}/api/visits/${id}`, {
        method: "DELETE",
        headers: { "X-User": user },
      });
      if (!response.ok) throw new Error("Falha ao cancelar");
      setMessage("Agendamento cancelado.");
      await loadEverything();
    } catch (error) {
      setMessage(error.message);
    }
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  const statusLabel = (status) => ({
    scheduled: "Agendada",
    completed: "Concluida",
    cancelled: "Cancelada",
  })[status] || status;

  return (
    <main className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">Polo Centro · ambiente demonstrativo</p>
          <h1>Planeje suas idas ao polo</h1>
          <p>Agende atividades presenciais e acompanhe o historico de visitas.</p>
        </div>
        <label className="user-picker">
          Perfil de demonstracao
          <select value={user} onChange={(event) => setUser(event.target.value)}>
            <option value="ana">Ana Demo</option>
            <option value="bruno">Bruno Demo</option>
          </select>
        </label>
      </header>

      <section className="summary" aria-label="Resumo de visitas">
        <article><span>Agendadas</span><strong>{summary.scheduled}</strong></article>
        <article><span>Concluidas</span><strong>{summary.completed}</strong></article>
        <article><span>Canceladas</span><strong>{summary.cancelled}</strong></article>
        <article><span>Total</span><strong>{summary.total}</strong></article>
      </section>

      {message && <div className="message" role="status">{message}</div>}

      <section className="workspace">
        <form className="visit-form" onSubmit={saveVisit}>
          <div className="section-title">
            <div>
              <p className="eyebrow">Agenda</p>
              <h2>{editingId ? "Alterar agendamento" : "Nova ida"}</h2>
            </div>
            {editingId && <button type="button" className="link" onClick={resetForm}>Sair da edicao</button>}
          </div>

          <label>
            Nome do visitante
            <input name="visitor_name" value={form.visitor_name} onChange={updateField} placeholder="Nome ficticio" />
          </label>
          <div className="row">
            <label>
              Data
              <input type="date" name="visit_date" value={form.visit_date} onChange={updateField} />
            </label>
            <label>
              Horario
              <input type="time" name="start_time" value={form.start_time} onChange={updateField} />
            </label>
          </div>
          <label>
            Finalidade
            <input name="purpose" value={form.purpose} onChange={updateField} placeholder="Aula, atendimento, laboratorio..." />
          </label>
          <label>
            Acompanhantes
            <input type="number" name="companions" value={form.companions} onChange={updateField} />
          </label>
          <label>
            Observacoes
            <textarea name="notes" rows="4" value={form.notes} onChange={updateField} placeholder="Informacoes uteis para a visita" />
          </label>
          <button className="primary" type="submit">{editingId ? "Salvar alteracoes" : "Agendar ida"}</button>
        </form>

        <div className="visits-panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">Historico</p>
              <h2>Visitas</h2>
            </div>
            <form className="search" onSubmit={(event) => { event.preventDefault(); loadEverything(); }}>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar" aria-label="Buscar visitas" />
              <button type="submit">Buscar</button>
            </form>
          </div>

          {loading && <p>Carregando...</p>}
          {!loading && visits.length === 0 && <p className="empty">Nenhuma visita encontrada.</p>}
          <div className="visit-list">
            {visits.map((visit, index) => (
              <article className="visit-card" key={index}>
                <div className="visit-heading">
                  <div>
                    <span className={`badge ${visit.status}`}>{statusLabel(visit.status)}</span>
                    <h3>{visit.purpose}</h3>
                  </div>
                  <div className="date"><strong>{visit.visit_date}</strong><span>{visit.start_time}</span></div>
                </div>
                <p>{visit.visitor_name} · {visit.companions} acompanhante(s)</p>
                <div className="notes" dangerouslySetInnerHTML={{ __html: visit.notes || "<em>Sem observacoes</em>" }} />
                {visit.status === "scheduled" && (
                  <div className="actions">
                    <button type="button" onClick={() => startEditing(visit)}>Alterar</button>
                    <button type="button" className="danger" onClick={() => cancelVisit(visit.id)}>Cancelar</button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

