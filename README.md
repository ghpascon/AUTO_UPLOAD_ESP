# AUTO_UPLOAD_ESP

Ferramenta em Python para:

- Gerar `littlefs.bin` a partir da pasta `data/`
- Detectar porta serial automaticamente (ou usar porta fixa)
- Gravar firmware completo no ESP32/ESP32-S3 com `esptool`
- Empacotar o projeto em executavel com `PyInstaller`

## Requisitos

- Python `3.11`
- Poetry `2.x`
- Binarios de firmware na pasta `bin_files/`
- Ferramentas de gravacao na pasta `esp_depend/`

Dependencias Python (definidas em `pyproject.toml`):

- `pyserial`
- `pyinstaller`

## Estrutura do projeto

```text
AUTO_UPLOAD_ESP/
	main.py               # Fluxo principal: gera LittleFS e grava firmware
	build_exe.py          # Build do executavel com PyInstaller
	config.json           # Configuracao de porta e tipo de chip
	bin_files/            # Binarios .bin do firmware + littlefs.bin
	data/                 # Arquivos para embutir no LittleFS
	esp_depend/           # esptool.exe, mklittlefs.exe, boot_app0.bin
```

## Configuracao

Edite `config.json`:

```json
{
	"com_port": "AUTO",
	"esp32s3": true
}
```

- `com_port`: `AUTO` para detectar automaticamente ou porta manual (ex.: `COM4`, `/dev/ttyUSB0`)
- `esp32s3`: `true` para ESP32-S3, `false` para ESP32 classico

## Como executar

1. Instale as dependencias:

```bash
poetry install
```

2. Execute o processo completo (gera LittleFS e faz upload):

```bash
poetry run python main.py
```

Fluxo executado pelo `main.py`:

1. Gera `bin_files/littlefs.bin` a partir de `data/`
2. Carrega configuracoes de `config.json`
3. Detecta porta serial (se `AUTO`)
4. Grava bootloader, partitions, boot_app0, app e LittleFS

## Build do executavel

Comando:

```bash
poetry run python build_exe.py
```

Por padrao, o executavel e gerado em:

- `TEMP/<nome_da_pasta_do_projeto>/`

Para customizar o diretorio base de saida, use variavel de ambiente:

```bash
EXE_PATH=/caminho/de/saida poetry run python build_exe.py
```

## Arquivos obrigatorios

Em `bin_files/`:

- `*.ino.bootloader.bin`
- `*.ino.partitions.bin`
- `*.ino.bin`
- `littlefs.bin` (gerado automaticamente)

Em `esp_depend/`:

- `esptool.exe`
- `mklittlefs.exe`
- `boot_app0.bin`

## Troubleshooting rapido

- Erro de porta serial:
	- verifique cabo USB e permissao da porta
	- teste definir `com_port` manualmente no `config.json`
- `littlefs.bin` nao gerado:
	- confirme existencia da pasta `data/`
	- confirme `esp_depend/mklittlefs.exe`
- Upload falhando repetidamente em `AUTO`:
	- force porta manual no `config.json`
	- reduza baud rate no codigo (se necessario)

## Observacoes de compatibilidade

- O projeto usa `esptool.exe` e `mklittlefs.exe` em `esp_depend/`, portanto o fluxo atual foi preparado para Windows.
- Em Linux/macOS, e necessario fornecer binarios/ferramentas equivalentes para o sistema operacional.

## Autor

- Gabriel Henrique Pascon