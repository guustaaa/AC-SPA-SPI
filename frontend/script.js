// JS puro com muitos Async's de mentira(JS não obedece thread safety kkkk)

let ehAdmin = false;

// Gerenciamento de login
async function fazerLogin() {
  let u = document.getElementById("usuario").value;
  let s = document.getElementById("senha").value;

  // verifica se campos estão vazios
  if (!u || !s) {
    alert("Preencha usuário e senha!");
    return;
  }

  //post de usuários para backend
  let res = await fetch("/usuarios/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario: u, senha: s })
  });

  //verifica resposta 
  if (!res.ok) {
    let err = await res.json();
    alert("Erro no login: " + (err.detail || res.status));
    return;
  }

  let data = await res.json();
  ehAdmin = data.eh_admin;

  //faz troca dos elementos após login
  document.getElementById("caixa-login").style.display = "none";
  document.getElementById("app").style.display = "block";
  document.getElementById("sidebar").style.display = "block";
  mostrarModulo("clientes");

  // remove centralização do body
  document.body.classList.remove("login-ativo");

  if (!ehAdmin) {
  // esconde o botão da sidebar para não admins
  let btnUsuarios = document.querySelector("#sidebar button[onclick=\"mostrarModulo('usuarios')\"]");
  if (btnUsuarios) btnUsuarios.style.display = "none";
}
}

// registra usuarios (apenas entra se for admin)
async function registrarUsuario() {
  let u = document.getElementById("novoUsuario").value;
  let s = document.getElementById("novaSenha").value;

  let res = await fetch("/usuarios/registrar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario: u, senha: s })
  });

  if (res.ok) {
    alert("Usuário registrado!");
  } else {
    let err = await res.json();
    alert("Erro: " + (err.detail || res.status));
  }
}

//listagem de usuarios 
async function listarUsuarios() {
  let res = await fetch("/usuarios/");
  let data = await res.json();

  let lista = document.getElementById("lista-usuarios");
  lista.innerHTML = "";

  data.forEach(u => {
    let li = document.createElement("li");
    li.innerText = u.usuario + (u.eh_admin ? " (admin)" : "");
    lista.appendChild(li);
  });
}


// função para exibir os modulos de maneira bruta manipulando o DOM
function mostrarModulo(secao) {
  document.getElementById("modulo-clientes").style.display = "none";
  document.getElementById("modulo-usuarios").style.display = "none";
  document.getElementById("modulo-cliente-view").style.display = "none";

  if (secao === "clientes") {
    document.getElementById("modulo-clientes").style.display = "block";
  } else if (secao === "usuarios" && ehAdmin) {
    document.getElementById("modulo-usuarios").style.display = "block";
  } else if (secao === "detalhe") {
    document.getElementById("modulo-cliente-view").style.display = "block";
  }
}

// Função de que adiciona clientes com backend
async function adicionarCliente() {
  let nome = document.getElementById("nome").value;
  let email = document.getElementById("email").value;
  //post de clientes
  await fetch("/clientes/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nome, email })
  });

  alert("Cliente adicionado!");
}
// listagem de clientes 
async function listarClientes() {
  let res = await fetch("/clientes/");
  let data = await res.json();

  let lista = document.getElementById("lista-clientes");
  lista.innerHTML = "";

  //verifica se existe dados no BD caso não exibe erro
  if (data.length === 0) {
    let li = document.createElement("li");
    li.innerText = "Nenhum cliente cadastrado.";
    li.style.color = "red";
    lista.appendChild(li);
    return;
  }

  // cria cada elemento de lista com dados do cliente
  data.forEach(c => {
    let li = document.createElement("li");
    li.innerText = c.nome + " - " + c.email;
    li.style.cursor = "pointer";
    li.onclick = () => mostrarDetalhe(c.id);
    lista.appendChild(li);
  });
}

// recupera dados do cliente
async function mostrarDetalhe(id) {
  let res = await fetch("/clientes/" + id);
  let dados = await res.json();

  if (dados.erro) {
    alert(dados.erro);
    return;
  }

  document.getElementById("info-cliente").innerHTML =
    "<p><b>ID:</b> " + dados.id + "</p>" +
    "<p><b>Nome:</b> " + dados.nome + "</p>" +
    "<p><b>Email:</b> " + dados.email + "</p>";

  mostrarModulo("detalhe");
}

// preenche cadastros para futuro uso no modo de uptade  <====== implementação futura, não utilizado ainda
async function preencherCadastro(id) {
  let res = await fetch("/clientes/" + id);
  let dados = await res.json();

  if (dados.erro) {
    alert(dados.erro);
    return;
  }

  // preenche inputs com os dados do cliente
  document.getElementById("nome").value = dados.nome;
  document.getElementById("email").value = dados.email;

  // mostra o modulo de clientes
  mostrarModulo("clientes");
}

// Ufa não aguentava mais mecher com JS puro