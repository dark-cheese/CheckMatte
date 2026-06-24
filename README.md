# CheckMatte

Agenda leve e local para monitoramento de vencimentos de certificados digitais. O CheckMatte varre pastas recursivamente, extrai automaticamente os dados de arquivos PFX, P12, CER, CRT, PEM e DER e organiza as datas de expiração em uma visualização mensal. O programa funciona offline e armazena as senhas de forma segura no cofre do Windows.

## Funcionalidades

- Suporte a múltiplos formatos: `.pfx`, `.p12`, `.cer`, `.crt`, `.pem`, `.der`
- Busca recursiva em subpastas a partir do diretório configurado
- Gerenciamento de múltiplas senhas: pool de senhas testadas automaticamente até encontrar a correta
- Armazenamento seguro das senhas no Windows Credential Manager (via `keyring`)
- Exibição mensal navegável com indicação visual de urgência
  - Vermelho: vencimento em 5 dias ou menos
  - Laranja: até 30 dias
  - Verde: mais de 30 dias
  - Cinza: já vencido
- Cache local para evitar releituras desnecessárias
- Log de erros detalhado para arquivos que não puderam ser lidos
- Interface totalmente silenciosa (sem pop-ups ou notificações nativas)
- Leve e portátil: executável único de aproximadamente 14 MB

## Requisitos

- Windows 10 ou superior
- Python 3.8+ (apenas para execução a partir do código-fonte)
- Bibliotecas Python: `cryptography`, `keyring`, `plyer`, `tkinter` (nativo)

## Instalação a partir do código-fonte

1. Clone o repositório ou baixe os arquivos.
2. Instale as dependências:

```bash
pip install -r requirements.txt