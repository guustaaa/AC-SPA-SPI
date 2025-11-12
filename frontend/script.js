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

  //Validação simples
  if (!u || !s) {
      alert("Usuário e Senha são obrigatórios!");
      return;
  }

  let res = await fetch("/usuarios/registrar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario: u, senha: s })
  });
  if (res.ok) {
    alert("Usuário registrado!");
    document.getElementById("novoUsuario").value = "";
    document.getElementById("novaSenha").value = "";
    listarUsuarios(); //Atualiza lista
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
    li.style.cursor = "pointer";
    //Adiciona clique para ver detalhe
    li.onclick = () => mostrarDetalheUsuario(u.id);
    lista.appendChild(li);
  });
}

//Mostrar config do usuário
async function mostrarDetalheUsuario(id) {
  let res = await fetch("/usuarios/" + id);
  let dados = await res.json();

  if (dados.erro) {
    alert(dados.erro);
    return;
  }

  document.getElementById("info-usuario").innerHTML =
    "<p><b>ID:</b> " + dados.id + "</p>" +
    "<p><b>Usuário:</b> " + dados.usuario + "</p>" +
    "<p><b>Nível:</b> " + (dados.eh_admin ? "Administrador" : "Padrão") + "</p>";
  
  mostrarModulo("detalhe-usuario");
}


// função para exibir os modulos de brutalmente manipulando o DOM
function mostrarModulo(secao) {
  // Oculta todos os módulos
  document.getElementById("modulo-clientes").style.display = "none";
  document.getElementById("modulo-usuarios").style.display = "none";
  document.getElementById("modulo-cliente-view").style.display = "none";
  document.getElementById("modulo-usuario-view").style.display = "none";
  document.getElementById("modulo-fornecedores").style.display = "none";
  document.getElementById("modulo-fornecedor-view").style.display = "none";
  document.getElementById("modulo-contas-receber").style.display = "none";
  document.getElementById("modulo-contas-pagar").style.display = "none";
  document.getElementById("modulo-cr-edit").style.display = "none"; 
  document.getElementById("modulo-cp-edit").style.display = "none";

  // Exibe o módulo solicitado
  if (secao === "clientes") {
    document.getElementById("modulo-clientes").style.display = "block";
  } else if (secao === "usuarios" && ehAdmin) {
    document.getElementById("modulo-usuarios").style.display = "block";
  } else if (secao === "detalhe") {
    document.getElementById("modulo-cliente-view").style.display = "block";
  } else if (secao === "detalhe-usuario") {
    document.getElementById("modulo-usuario-view").style.display = "block";
  } else if (secao === "fornecedores") {
    document.getElementById("modulo-fornecedores").style.display = "block";
  } else if (secao === "detalhe-fornecedor") {
    document.getElementById("modulo-fornecedor-view").style.display = "block";
  } else if (secao === "contas-receber") {
    document.getElementById("modulo-contas-receber").style.display = "block";
    popularDropdownClientes(); //Popula dropdowns
  } else if (secao === "contas-pagar") {
    document.getElementById("modulo-contas-pagar").style.display = "block";
    popularDropdownFornecedores(); //Popula dropdowns
  } else if (secao === "cr-edit") { 
    document.getElementById("modulo-cr-edit").style.display = "block";
  } else if (secao === "cp-edit") { 
    document.getElementById("modulo-cp-edit").style.display = "block";
  }
}

// --- MÓDULO DE CLIENTES ---

//Consulta CNPJ
async function buscarCNPJ(tipo) {
  // tipo pode ser 'cliente' ou 'fornecedor'
  let cnpj = document.getElementById(tipo + "-cnpj").value.replace(/\D/g, ''); 
  if (cnpj.length !== 14) {
    alert("Digite um CNPJ válido com 14 números.");
    return;
  }
  
  try {
    let res = await fetch("/consulta-cnpj/" + cnpj);
    if (!res.ok) {
        let err = await res.json();
        throw new Error(err.detail || "Erro ao consultar CNPJ");
    }
    let dados = await res.json();
    
    // Preenche o formulário
    document.getElementById(tipo + "-razao_social").value = dados.razao_social || "";
    document.getElementById(tipo + "-nome_fantasia").value = dados.nome_fantasia || "";
    document.getElementById(tipo + "-ie").value = dados.ie || "";
    document.getElementById(tipo + "-email").value = dados.email || "";
    document.getElementById(tipo + "-cep").value = dados.cep || "";
    document.getElementById(tipo + "-rua").value = dados.rua || "";
    document.getElementById(tipo + "-numero").value = dados.numero || "";
    document.getElementById(tipo + "-bairro").value = dados.bairro || "";
    document.getElementById(tipo + "-cidade").value = dados.cidade || "";
    document.getElementById(tipo + "-estado").value = dados.estado || "";

  } catch (error) {
    alert("Erro na API: " + error.message);
  }
}

// Função de que adiciona/edita clientes com backend
async function salvarCliente() {
  let idEdit = document.getElementById("clienteIdEdit").value;
  
  //Coleta todos os dados do form
  let dadosCliente = {
    cnpj: document.getElementById("cliente-cnpj").value.replace(/\D/g, ''),
    razao_social: document.getElementById("cliente-razao_social").value,
    nome_fantasia: document.getElementById("cliente-nome_fantasia").value,
    ie: document.getElementById("cliente-ie").value,
    email: document.getElementById("cliente-email").value,
    cep: document.getElementById("cliente-cep").value,
    rua: document.getElementById("cliente-rua").value,
    numero: document.getElementById("cliente-numero").value,
    bairro: document.getElementById("cliente-bairro").value,
    cidade: document.getElementById("cliente-cidade").value,
    estado: document.getElementById("cliente-estado").value,
    nome: document.getElementById("cliente-nome_fantasia").value // Campo antigo
  };

  //Validação
  if (!dadosCliente.cnpj || !dadosCliente.razao_social) {
      alert("CNPJ e Razão Social são obrigatórios!");
      return;
  }

  let url = "/clientes/";
  let method = "POST";

  //Se tem ID, é edição (PUT)
  if (idEdit) {
    url = "/clientes/" + idEdit;
    method = "PUT";
  }

  //post de clientes
  let res = await fetch(url, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dadosCliente)
  });
  
  if (res.ok) {
    alert("Cliente salvo com sucesso!");
    limparFormCliente();
    listarClientes();
  } else {
    let err = await res.json();
    alert("Erro ao salvar cliente: " + (err.detail || res.status));
  }
}

//Limpa o form de cliente
function limparFormCliente() {
    document.getElementById("clienteIdEdit").value = "";
    document.getElementById("cliente-cnpj").value = "";
    document.getElementById("cliente-razao_social").value = "";
    document.getElementById("cliente-nome_fantasia").value = "";
    document.getElementById("cliente-ie").value = "";
    document.getElementById("cliente-email").value = "";
    document.getElementById("cliente-cep").value = "";
    document.getElementById("cliente-rua").value = "";
    document.getElementById("cliente-numero").value = "";
    document.getElementById("cliente-bairro").value = "";
    document.getElementById("cliente-cidade").value = "";
    document.getElementById("cliente-estado").value = "";
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
    // Exibe nome fantasia/razão social
    li.innerText = (c.nome_fantasia || c.razao_social) + " - " + c.cnpj;
    li.style.cursor = "pointer";
    li.onclick = () => mostrarDetalhe(c); // Passa o objeto
    lista.appendChild(li);
  });
}

// recupera dados do cliente
async function mostrarDetalhe(cliente) {
  // Recebe o objeto cliente
  let infoDiv = document.getElementById("info-cliente");
  
  // Exibe todos os dados
  infoDiv.innerHTML =
    "<p><b>ID:</b> " + cliente.id + "</p>" +
    "<p><b>CNPJ:</b> " + cliente.cnpj + "</p>" +
    "<p><b>Razão Social:</b> " + cliente.razao_social + "</p>" +
    "<p><b>Nome Fantasia:</b> " + (cliente.nome_fantasia || "N/A") + "</p>" +
    "<p><b>I.E:</b> " + (cliente.ie || "N/A") + "</p>" +
    "<p><b>Email:</b> " + (cliente.email || "N/A") + "</p>" +
    "<h3>Endereço</h3>" +
    "<p><b>CEP:</b> " + (cliente.cep || "N/A") + "</p>" +
    "<p>" + (cliente.rua || "N/A") + ", " + (cliente.numero || "N/A") + " - " + (cliente.bairro || "N/A") + "</p>" +
    "<p>" + (cliente.cidade || "N/A") + " - " + (cliente.estado || "N/A") + "</p>" +
    "<br><button onclick='prepararEdicaoCliente(" + cliente.id + ")'>Editar Cliente</button>"; //Botão Editar
    
  mostrarModulo("detalhe");
}

//Prepara o form para edição
async function prepararEdicaoCliente(id) {
    let res = await fetch("/clientes/" + id);
    let dados = await res.json();
    if (dados.erro) {
        alert(dados.erro);
        return;
    }

    // preenche inputs com os dados do cliente
    document.getElementById("clienteIdEdit").value = dados.id;
    document.getElementById("cliente-cnpj").value = dados.cnpj || "";
    document.getElementById("cliente-razao_social").value = dados.razao_social || "";
    document.getElementById("cliente-nome_fantasia").value = dados.nome_fantasia || "";
    document.getElementById("cliente-ie").value = dados.ie || "";
    document.getElementById("cliente-email").value = dados.email || "";
    document.getElementById("cliente-cep").value = dados.cep || "";
    document.getElementById("cliente-rua").value = dados.rua || "";
    document.getElementById("cliente-numero").value = dados.numero || "";
    document.getElementById("cliente-bairro").value = dados.bairro || "";
    document.getElementById("cliente-cidade").value = dados.cidade || "";
    document.getElementById("cliente-estado").value = dados.estado || "";
    
    // mostra o modulo de clientes
    mostrarModulo("clientes");
}


// --- MÓDULO DE FORNECEDORES---

//Salva ou Edita fornecedor
async function salvarFornecedor() {
  let idEdit = document.getElementById("fornecedorIdEdit").value;
  
  let dadosFornecedor = {
    cnpj: document.getElementById("fornecedor-cnpj").value.replace(/\D/g, ''),
    razao_social: document.getElementById("fornecedor-razao_social").value,
    nome_fantasia: document.getElementById("fornecedor-nome_fantasia").value,
    ie: document.getElementById("fornecedor-ie").value,
    email: document.getElementById("fornecedor-email").value,
    cep: document.getElementById("fornecedor-cep").value,
    rua: document.getElementById("fornecedor-rua").value,
    numero: document.getElementById("fornecedor-numero").value,
    bairro: document.getElementById("fornecedor-bairro").value,
    cidade: document.getElementById("fornecedor-cidade").value,
    estado: document.getElementById("fornecedor-estado").value
  };

  if (!dadosFornecedor.cnpj || !dadosFornecedor.razao_social) {
      alert("CNPJ e Razão Social são obrigatórios!");
      return;
  }

  let url = "/fornecedores/";
  let method = "POST";

  //Verifica se é edição
  if (idEdit) {
    url = "/fornecedores/" + idEdit;
    method = "PUT";
  }
  
  let res = await fetch(url, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dadosFornecedor)
  });
  
  if (res.ok) {
    alert("Fornecedor salvo com sucesso!");
    limparFormFornecedor();
    listarFornecedores();
    mostrarModulo("fornecedores"); // Garante que volte para a lista
  } else {
    let err = await res.json();
    alert("Erro ao salvar fornecedor: " + (err.detail || res.status));
  }
}

//Limpa form fornecedor
function limparFormFornecedor() {
    document.getElementById("fornecedorIdEdit").value = "";
    document.getElementById("fornecedor-cnpj").value = "";
    document.getElementById("fornecedor-razao_social").value = "";
    document.getElementById("fornecedor-nome_fantasia").value = "";
    document.getElementById("fornecedor-ie").value = "";
    document.getElementById("fornecedor-email").value = "";
    document.getElementById("fornecedor-cep").value = "";
    document.getElementById("fornecedor-rua").value = "";
    document.getElementById("fornecedor-numero").value = "";
    document.getElementById("fornecedor-bairro").value = "";
    document.getElementById("fornecedor-cidade").value = "";
    document.getElementById("fornecedor-estado").value = "";
}

//Lista fornecedores
async function listarFornecedores() {
  let res = await fetch("/fornecedores/");
  let data = await res.json();

  let lista = document.getElementById("lista-fornecedores");
  lista.innerHTML = "";
  if (data.length === 0) {
    lista.innerHTML = "<li style='color:red;'>Nenhum fornecedor cadastrado.</li>";
    return;
  }
  data.forEach(f => {
    let li = document.createElement("li");
    li.innerText = (f.nome_fantasia || f.razao_social) + " - " + f.cnpj;
    li.style.cursor = "pointer";
    li.onclick = () => mostrarDetalheFornecedor(f);
    lista.appendChild(li);
  });
}

//Mostra config fornecedor com botão de edição
async function mostrarDetalheFornecedor(fornecedor) {
  let infoDiv = document.getElementById("info-fornecedor");
  
  //Adiciona todos os campos e o botão de editar
  infoDiv.innerHTML =
    "<p><b>ID:</b> " + fornecedor.id + "</p>" +
    "<p><b>CNPJ:</b> " + fornecedor.cnpj + "</p>" +
    "<p><b>Razão Social:</b> " + fornecedor.razao_social + "</p>" +
    "<p><b>Nome Fantasia:</b> " + (fornecedor.nome_fantasia || "N/A") + "</p>" +
    "<p><b>I.E:</b> " + (fornecedor.ie || "N/A") + "</p>" +
    "<p><b>Email:</b> " + (fornecedor.email || "N/A") + "</p>" +
    "<h3>Endereço</h3>" +
    "<p><b>CEP:</b> " + (fornecedor.cep || "N/A") + "</p>" +
    "<p>" + (fornecedor.rua || "N/A") + ", " + (fornecedor.numero || "N/A") + " - " + (fornecedor.bairro || "N/A") + "</p>" +
    "<p>" + (fornecedor.cidade || "N/A") + " - " + (fornecedor.estado || "N/A") + "</p>" +
    "<br><button onclick='prepararEdicaoFornecedor(" + fornecedor.id + ")'>Editar Fornecedor</button>"; // (Novo) Botão Editar
    
  mostrarModulo("detalhe-fornecedor");
}

//Prepara o form para edição de fornecedor
async function prepararEdicaoFornecedor(id) {
  let res = await fetch("/fornecedores/" + id);
  let dados = await res.json();
  if (dados.erro) {
      alert(dados.erro);
      return;
  }

  // preenche inputs com os dados do fornecedor
  document.getElementById("fornecedorIdEdit").value = dados.id;
  document.getElementById("fornecedor-cnpj").value = dados.cnpj || "";
  document.getElementById("fornecedor-razao_social").value = dados.razao_social || "";
  document.getElementById("fornecedor-nome_fantasia").value = dados.nome_fantasia || "";
  document.getElementById("fornecedor-ie").value = dados.ie || "";
  document.getElementById("fornecedor-email").value = dados.email || "";
  document.getElementById("fornecedor-cep").value = dados.cep || "";
  document.getElementById("fornecedor-rua").value = dados.rua || "";
  document.getElementById("fornecedor-numero").value = dados.numero || "";
  document.getElementById("fornecedor-bairro").value = dados.bairro || "";
  document.getElementById("fornecedor-cidade").value = dados.cidade || "";
  document.getElementById("fornecedor-estado").value = dados.estado || "";
  
  // mostra o modulo de fornecedores
  mostrarModulo("fornecedores");
}

// --- MÓDULO FINANCEIRO---

//Popula dropdown de clientes (form e filtro)
async function popularDropdownClientes() {
    let res = await fetch("/clientes/");
    let data = await res.json();
    
    let selectForm = document.getElementById("cr-cliente-id");
    let selectFiltro = document.getElementById("filtro-cr-cliente");
    
    selectForm.innerHTML = "<option value=''>Selecione o Cliente</option>";
    selectFiltro.innerHTML = "<option value=''>Todos Clientes</option>";

    data.forEach(c => {
        let nome = c.nome_fantasia || c.razao_social;
        selectForm.innerHTML += `<option value="${c.id}">${nome}</option>`;
        selectFiltro.innerHTML += `<option value="${c.id}">${nome}</option>`;
    });
}

//Popula dropdown de fornecedores (form e filtro)
async function popularDropdownFornecedores() {
    let res = await fetch("/fornecedores/");
    let data = await res.json();
    
    let selectForm = document.getElementById("cp-fornecedor-id");
    let selectFiltro = document.getElementById("filtro-cp-fornecedor");
    
    selectForm.innerHTML = "<option value=''>Selecione o Fornecedor</option>";
    selectFiltro.innerHTML = "<option value=''>Todos Fornecedores</option>";

    data.forEach(f => {
        let nome = f.nome_fantasia || f.razao_social;
        selectForm.innerHTML += `<option value="${f.id}">${nome}</option>`;
        selectFiltro.innerHTML += `<option value="${f.id}">${nome}</option>`;
    });
}

//Adiciona conta a receber
async function adicionarContaReceber() {
    let dados = {
        cliente_id: document.getElementById("cr-cliente-id").value,
        descricao: document.getElementById("cr-descricao").value,
        valor: document.getElementById("cr-valor").value,
        data_vencimento: document.getElementById("cr-data-vencimento").value
    };

    if (!dados.cliente_id || !dados.descricao || !dados.valor || !dados.data_vencimento) {
        alert("Preencha todos os campos obrigatórios!");
        return;
    }

    await fetch("/contas-receber/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados)
    });
    
    alert("Conta a receber adicionada!");
    listarContasReceber(); 
}

//Lista contas a receber com filtros e totais
async function listarContasReceber() {
    let cliente_id = document.getElementById("filtro-cr-cliente").value;
    let status = document.getElementById("filtro-cr-status").value;
    let data_inicio = document.getElementById("filtro-cr-data-inicio").value;
    let data_fim = document.getElementById("filtro-cr-data-fim").value;

    let params = new URLSearchParams();
    if (cliente_id) params.append("cliente_id", cliente_id);
    if (status) params.append("status", status);
    if (data_inicio) params.append("data_inicio", data_inicio);
    if (data_fim) params.append("data_fim", data_fim);

    let res = await fetch("/contas-receber/?" + params.toString());
    let data = await res.json();
    
    let lista = document.getElementById("lista-contas-receber");
    lista.innerHTML = "";
    
    // Lógica de Totais
    let totalReceber = 0;
    let totalAtrasado = 0;
    const hoje = new Date().toISOString().split('T')[0];

    if (data.length === 0) {
        lista.innerHTML = "<li style='color:red;'>Nenhum lançamento encontrado.</li>";
    }
    
    data.forEach(c => {
        // Soma totais pendentes
        if (c.status !== 'pago') {
            totalReceber += c.valor;
            // Verifica atrasados
            if (c.data_vencimento < hoje) {
                totalAtrasado += c.valor;
            }
        }

        let li = document.createElement("li");
        let valorTxt = `R$ ${c.valor_pago.toFixed(2)} / R$ ${c.valor.toFixed(2)}`;
        li.innerText = `[${c.status}] ${c.data_vencimento} - ${valorTxt} - ${c.descricao} (${c.cliente_nome})`;
        
        // corzinha Atrasado
        if (c.status !== 'pago' && c.data_vencimento < hoje) {
            li.style.color = "#E74C3C"; // Vermelho
        }
        // corzinha Pago
        if (c.status === 'pago') {
            li.style.color = "#4CAF50"; // Verde
            li.style.textDecoration = "line-through";
        }

        li.style.cursor = "pointer";
        li.onclick = () => abrirEdicaoCR(c); // Abre edição
        
        lista.appendChild(li);
    });
    
    // Atualiza Totais na UI
    document.getElementById("cr-total").innerText = `R$ ${totalReceber.toFixed(2)}`;
    document.getElementById("cr-atrasado").innerText = `R$ ${totalAtrasado.toFixed(2)}`;
}

//Adiciona conta a pagar
async function adicionarContaPagar() {
    let dados = {
        fornecedor_id: document.getElementById("cp-fornecedor-id").value,
        descricao: document.getElementById("cp-descricao").value,
        valor: document.getElementById("cp-valor").value,
        data_vencimento: document.getElementById("cp-data-vencimento").value
    };

    if (!dados.fornecedor_id || !dados.descricao || !dados.valor || !dados.data_vencimento) {
        alert("Preencha todos os campos obrigatórios!");
        return;
    }

    await fetch("/contas-pagar/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados)
    });
    
    alert("Conta a pagar adicionada!");
    listarContasPagar(); 
}

//Lista contas a pagar com filtros e totais
async function listarContasPagar() {
    let fornecedor_id = document.getElementById("filtro-cp-fornecedor").value;
    let status = document.getElementById("filtro-cp-status").value;
    let data_inicio = document.getElementById("filtro-cp-data-inicio").value;
    let data_fim = document.getElementById("filtro-cp-data-fim").value;

    let params = new URLSearchParams();
    if (fornecedor_id) params.append("fornecedor_id", fornecedor_id);
    if (status) params.append("status", status);
    if (data_inicio) params.append("data_inicio", data_inicio);
    if (data_fim) params.append("data_fim", data_fim);

    let res = await fetch("/contas-pagar/?" + params.toString());
    let data = await res.json();
    
    let lista = document.getElementById("lista-contas-pagar");
    lista.innerHTML = "";
    
    let totalPagar = 0;
    let totalAtrasado = 0;
    const hoje = new Date().toISOString().split('T')[0];
    
    if (data.length === 0) {
         lista.innerHTML = "<li style='color:red;'>Nenhum lançamento encontrado.</li>";
    }
    
    data.forEach(c => {
        if (c.status !== 'pago') {
            totalPagar += c.valor;
            if (c.data_vencimento < hoje) {
                totalAtrasado += c.valor;
            }
        }
        
        let li = document.createElement("li");
        let valorTxt = `R$ ${c.valor_pago.toFixed(2)} / R$ ${c.valor.toFixed(2)}`;
        li.innerText = `[${c.status}] ${c.data_vencimento} - ${valorTxt} - ${c.descricao} (${c.fornecedor_nome})`;
        
        if (c.status !== 'pago' && c.data_vencimento < hoje) {
            li.style.color = "#E74C3C";
        }
        if (c.status === 'pago') {
             li.style.color = "#4CAF50";
             li.style.textDecoration = "line-through";
        }

        li.style.cursor = "pointer";
        li.onclick = () => abrirEdicaoCP(c); // Abre edição
        
        lista.appendChild(li);
    });
    
    // Atualiza totais
    document.getElementById("cp-total").innerText = `R$ ${totalPagar.toFixed(2)}`;
    document.getElementById("cp-atrasado").innerText = `R$ ${totalAtrasado.toFixed(2)}`;
}

//Funções de Alterar CR e CP
function abrirEdicaoCR(conta) {
    document.getElementById("edit-cr-id").value = conta.id;
    document.getElementById("edit-cr-descricao").innerText = conta.descricao;
    document.getElementById("edit-cr-cliente").innerText = conta.cliente_nome;
    document.getElementById("edit-cr-valor-total").innerText = `R$ ${conta.valor.toFixed(2)}`;
    document.getElementById("edit-cr-valor-pago").value = conta.valor_pago;
    
    mostrarModulo("cr-edit");
}

function abrirEdicaoCP(conta) {
    document.getElementById("edit-cp-id").value = conta.id;
    document.getElementById("edit-cp-descricao").innerText = conta.descricao;
    document.getElementById("edit-cp-fornecedor").innerText = conta.fornecedor_nome;
    document.getElementById("edit-cp-valor-total").innerText = `R$ ${conta.valor.toFixed(2)}`;
    document.getElementById("edit-cp-valor-pago").value = conta.valor_pago;
    
    mostrarModulo("cp-edit");
}

//Salva o pagamento da conta a receber
async function salvarPagamentoCR() {
    let id = document.getElementById("edit-cr-id").value;
    let valorPago = document.getElementById("edit-cr-valor-pago").value;

    if (valorPago === "" || valorPago === null || parseFloat(valorPago) < 0) {
        alert("Por favor, informe um valor pago válido.");
        return;
    }
    
    let res = await fetch(`/contas-receber/${id}/pagar`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ valor_pago: parseFloat(valorPago) })
    });

    if (res.ok) {
        alert("Pagamento atualizado!");
        mostrarModulo("contas-receber");
        listarContasReceber(); // Atualiza a lista
    } else {
        let err = await res.json();
        alert("Erro ao salvar: " + (err.detail || res.status));
    }
}

//Salva o pagamento da conta a pagar
async function salvarPagamentoCP() {
    let id = document.getElementById("edit-cp-id").value;
    let valorPago = document.getElementById("edit-cp-valor-pago").value;
    
    if (valorPago === "" || valorPago === null || parseFloat(valorPago) < 0) {
        alert("Por favor, informe um valor pago válido.");
        return;
    }

    let res = await fetch(`/contas-pagar/${id}/pagar`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ valor_pago: parseFloat(valorPago) })
    });
    
    if (res.ok) {
        alert("Pagamento atualizado!");
        mostrarModulo("contas-pagar");
        listarContasPagar(); // Atualiza a lista
    } else {
        let err = await res.json();
        alert("Erro ao salvar: " + (err.detail || res.status));
    }
}
