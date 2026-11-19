"""Painel de acompanhamento em tempo real (uma página HTML que consulta a API a cada segundo)."""

PAINEL_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Broker - Painel</title>
<style>
  :root { --fundo:#f4f5f7; --cartao:#fff; --borda:#d9dde3; --texto:#1b1f24; --suave:#5f6b7a; --azul:#1f3864; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, Arial, sans-serif; background:var(--fundo); color:var(--texto); }
  header { background:var(--azul); color:#fff; padding:14px 24px; display:flex; justify-content:space-between; align-items:center; }
  header h1 { font-size:18px; margin:0; }
  #status { font-size:13px; opacity:.9; }
  main { padding:20px 24px; display:grid; gap:16px; }
  .cartoes { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }
  .cartao { background:var(--cartao); border:1px solid var(--borda); border-radius:8px; padding:12px 14px; }
  .cartao .valor { font-size:28px; font-weight:700; }
  .cartao .rotulo { font-size:12px; color:var(--suave); text-transform:uppercase; letter-spacing:.04em; }
  .painel { background:var(--cartao); border:1px solid var(--borda); border-radius:8px; padding:14px 16px; overflow-x:auto; }
  .painel h2 { font-size:14px; margin:0 0 10px; color:var(--azul); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--borda); vertical-align:top; }
  th { color:var(--suave); font-weight:600; }
  .vazio { color:var(--suave); font-size:13px; }
  .tag { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px; font-weight:600; color:#fff; }
  .publicada{background:#2b6cb0} .entregue{background:#2f855a} .falhou{background:#b7791f}
  .esgotada{background:#c53030} .descartada,.retida{background:#718096} .reprocessada{background:#6b46c1}
  .duas { display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:16px; }
  button { cursor:pointer; border:1px solid var(--azul); background:#fff; color:var(--azul); border-radius:6px; padding:3px 10px; font-size:12px; }
  button:hover { background:var(--azul); color:#fff; }
  .erro-topo { color:#c53030; }
</style>
</head>
<body>
<header>
  <h1>Broker - painel em tempo real</h1>
  <span id="status">conectando...</span>
</header>
<main>
  <section class="cartoes" id="cartoes"></section>
  <section class="painel"><h2>Tópicos e assinantes</h2><div id="topicos"></div></section>
  <section class="duas">
    <div class="painel"><h2>Filas</h2><div id="filas"></div></div>
    <div class="painel"><h2>Fila de erros</h2><div id="erros"></div></div>
  </section>
  <section class="painel"><h2>Histórico (mais recentes primeiro)</h2><div id="historico"></div></section>
</main>
<script>
const params = new URLSearchParams(location.search);
const chave = params.get("chave");
const cabecalhos = chave ? {"X-API-Key": chave} : {};

async function pegar(caminho) {
  const r = await fetch(caminho, {headers: cabecalhos});
  if (!r.ok) throw new Error(caminho + " respondeu " + r.status);
  return r.json();
}
function el(tag, texto, classe) {
  const e = document.createElement(tag);
  if (texto !== undefined && texto !== null) e.textContent = String(texto);
  if (classe) e.className = classe;
  return e;
}
function limpar(id) {
  const n = document.getElementById(id);
  while (n.firstChild) n.removeChild(n.firstChild);
  return n;
}
function tabela(colunas, linhas) {
  const t = el("table"), cab = el("tr");
  colunas.forEach(c => cab.appendChild(el("th", c)));
  t.appendChild(cab);
  linhas.forEach(l => {
    const tr = el("tr");
    l.forEach(c => {
      const td = el("td");
      if (c instanceof Node) td.appendChild(c); else td.textContent = c === null ? "" : String(c);
      tr.appendChild(td);
    });
    t.appendChild(tr);
  });
  return t;
}

function desenharCartoes(totais) {
  const alvo = limpar("cartoes");
  [["Publicadas", totais.publicadas], ["Entregas ok", totais.entregues],
   ["Falhas de entrega", totais.falhas], ["Na fila de erros", totais.na_fila_de_erros]]
    .forEach(([rotulo, valor]) => {
      const c = el("div", null, "cartao");
      c.appendChild(el("div", valor, "valor"));
      c.appendChild(el("div", rotulo, "rotulo"));
      alvo.appendChild(c);
    });
}
function desenharTopicos(topicos) {
  const alvo = limpar("topicos");
  if (!topicos.length) { alvo.appendChild(el("p", "Nenhum tópico ainda.", "vazio")); return; }
  const linhas = [];
  topicos.forEach(t => {
    if (!t.assinantes.length) linhas.push([t.nome, t.publicadas, "(sem assinantes)", "", "", "", ""]);
    t.assinantes.forEach((a, i) => linhas.push([
      i === 0 ? t.nome : "", i === 0 ? t.publicadas : "", a.destino,
      a.ativa ? "ativa" : "inativa", a.pendentes, a.entregues, a.falhas]));
  });
  alvo.appendChild(tabela(
    ["Tópico", "Publicadas", "Assinante", "Situação", "Pendentes", "Entregues", "Falhas"], linhas));
}
function desenharFilas(filas) {
  const alvo = limpar("filas");
  alvo.appendChild(tabela(["Fila", "Pendentes"], filas.map(f => [f.nome, f.pendentes])));
}
function desenharErros(erros) {
  const alvo = limpar("erros");
  if (!erros.length) { alvo.appendChild(el("p", "Nenhuma mensagem com falha definitiva.", "vazio")); return; }
  const linhas = erros.map(e => {
    const botao = el("button", "Reprocessar");
    botao.onclick = async () => {
      botao.disabled = true;
      try {
        await fetch("/erros/" + encodeURIComponent(e.id) + "/reprocessar",
                    {method: "POST", headers: cabecalhos});
      } finally { atualizar(); }
    };
    return [e.id.slice(0, 8), e.topico, e.motivos.join(" | "), botao];
  });
  alvo.appendChild(tabela(["Mensagem", "Tópico", "Motivo", ""], linhas));
}
function desenharHistorico(eventos) {
  const alvo = limpar("historico");
  if (!eventos.length) { alvo.appendChild(el("p", "Sem eventos ainda.", "vazio")); return; }
  const linhas = eventos.slice().reverse().map(e => [
    new Date(e.hora).toLocaleTimeString(),
    el("span", e.tipo, "tag " + e.tipo),
    e.topico, e.mensagem ? e.mensagem.slice(0, 8) : "", e.destino || "", e.detalhe || ""]);
  alvo.appendChild(tabela(["Hora", "Evento", "Tópico", "Mensagem", "Assinatura", "Detalhe"], linhas));
}

let ocupado = false;
async function atualizar() {
  if (ocupado) return;
  ocupado = true;
  const status = document.getElementById("status");
  try {
    const [estado, erros, historico] = await Promise.all([
      pegar("/estado"), pegar("/erros"), pegar("/historico?limite=60")]);
    desenharCartoes(estado.totais);
    desenharTopicos(estado.topicos);
    desenharFilas(estado.filas);
    desenharErros(erros.erros);
    desenharHistorico(historico.eventos);
    status.className = "";
    status.textContent = "atualizado às " + new Date().toLocaleTimeString() + " (a cada 1 s)";
  } catch (e) {
    status.className = "erro-topo";
    status.textContent = "sem conexão com o Broker: " + e.message;
  } finally { ocupado = false; }
}
atualizar();
setInterval(atualizar, 1000);
</script>
</body>
</html>
"""
