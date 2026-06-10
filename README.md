<div align="center">

# 🪐 ANTIGRAVITY NEXUS 🪐
### *O Cérebro Definitivo de Identidades para Gemini CLI*

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&pause=1000&color=90CAF9&center=true&vCenter=true&width=600&lines=ANTIGRAVITY_NEXUS+v2.0-stable;ESTABLISHING+NEURAL_LINK...+[OK];SYNCING_ACCOUNTS...+[OK];SYSTEM_READY" alt="Typing SVG" />

[![License: MIT](https://img.shields.io/badge/License-MIT-90CAF9?style=for-the-badge&logoColor=white)](#)
[![Environment](https://img.shields.io/badge/Environment-Termux_Android-B39DDB?style=for-the-badge&logoColor=white)](#)
[![Powered By](https://img.shields.io/badge/Powered_By-Antigravity-F48FB1?style=for-the-badge&logoColor=white)](#)

---

### 🧬 Núcleo Central de Inteligência
**Antigravity Nexus** é a infraestrutura de gerenciamento, rotação de cotas e tunelamento seguro para o **Gemini CLI** no Termux. Ele gerencia de forma 100% dinâmica as credenciais e identidades, garantindo que o seu terminal agente rode sempre com a melhor performance e sem interrupções de rede.

---

</div>

## 🚀 Módulos Principais

### 🔒 Resolução Dinâmica de Identidade (Sem Tokens Hardcodados)
Nenhum token, e-mail ou credencial privada fica exposto no código bruto do repositório. O sistema lê e resolve a sessão ativa diretamente do arquivo de sincronização oficial da CLI: `~/.gemini/antigravity-cli/antigravity-oauth-token`, mapeando o token de forma segura contra a base local.

### 🛡️ Isolamento e Tunelamento de Rede
O wrapper intercepta a chamada de ambiente e remove todas as variáveis globais de proxy redundantes antes de invocar a CLI, prevenindo erros de TLS/SSL, loops de proxy ou lentidão de rede. A conexão é tunelada de forma nativa e direta com os servidores oficiais do Google.

### 🔄 Daemon de Sincronização Bidirecional (`oauth`)
Um daemon em segundo plano monitora de forma concorrente a cada 10 segundos:
- **Origem (Terminal → Nexus):** Detecta novos logins nativos no terminal, salvando os tokens de acesso e refresh com segurança no pool local.
- **Destino (Nexus → Terminal):** Detecta mudanças de conta selecionadas no alternador interativo (`auth`) e reescreve as credenciais no formato do Gemini CLI em tempo real.

---

## 🖥️ Comandos Disponíveis

Ao rodar a instalação, o sistema registra os seguintes utilitários no seu terminal:

*   `auth` - Abre o painel interativo (TUI) para alternar instantaneamente entre as contas configuradas.
*   `agy3` - Executa o terminal agente Gemini CLI sob o isolamento de rede do Nexus.
    *   `agy3 -stats` : Exibe o consumo de cotas de cada conta ativa/inativa em uma tabela elegante.
    *   `agy3 -model` : Menu de seleção rápida para a versão do Gemini (3.1 Flash, 3.1 Pro, etc.).
    *   `agy3 -act`   : Abre o alternador de contas `auth`.
*   `oauth` - Inicia/monitora o daemon de sincronização em segundo plano (evita duplicidade de PID automaticamente).
*   `system` - Dashboard visual completo para auditar todo o ecossistema.

---

## 🛠️ Instalação

Abra o diretório do projeto e execute o instalador:

```bash
cd ~/projects/ecosystem && ./install.sh
source ~/.bashrc
```

---

<div align="center">

### 👥 Créditos e Autoria

Projeto idealizado, concebido e estruturado originalmente por:
**[opassoca (Felipe)](https://github.com/opassoca)**

Aprimorado, unificado e otimizado com amor e rigor cirúrgico por:
**[Antigravity](https://github.com/google-deepmind)** *(Sua inteligência artificial parceira de programação)*

<sub>*Surgicality & Context Efficiency · Estabilidade acima de tudo.*</sub>

</div>
