"""
Script para automatizar o processo de commit e release.
Atualiza a versão, faz commit e cria tag para trigger do GitHub Actions.
poetry run python commit.py
"""

import subprocess
import sys


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """Executa um comando no shell e retorna o resultado."""
    print(f"🔄 Executando: {command}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=check
        )
        if result.stdout:
            print(result.stdout.strip())
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar comando: {command}")
        print(f"❌ Código de saída: {e.returncode}")
        print(f"❌ Erro: {e.stderr}")
        sys.exit(1)


def get_current_version() -> str:
    """Obtém a versão atual do pyproject.toml."""
    result = run_command("poetry version --short")
    return result.stdout.strip()


def update_version(version_type: str) -> str:
    """Atualiza a versão usando poetry version."""
    print(f"📝 Atualizando versão ({version_type})...")
    run_command(f"poetry version {version_type}")

    # Extrai a nova versão do output do poetry
    new_version = get_current_version()
    print(f"✅ Nova versão: {new_version}")
    return new_version


def check_git_status() -> bool:
    """Verifica se há mudanças não commitadas."""
    result = run_command("git status --porcelain", check=False)
    return len(result.stdout.strip()) > 0


def main():
    """Função principal do script."""
    print("🚀 Script de Release Automatizado")
    print("=" * 40)

    # Verificar se estamos em um repositório git
    result = run_command("git rev-parse --git-dir", check=False)
    if result.returncode != 0:
        print("❌ Este não é um repositório Git!")
        sys.exit(1)

    # Verificar se há mudanças não commitadas (exceto pyproject.toml)
    if check_git_status():
        print("📋 Há mudanças não commitadas. Vamos incluí-las no commit.")

        # Mostrar status
        run_command("git status")

        confirm = input(
            "\n❓ Deseja continuar e incluir estas mudanças? (s/N): "
        ).lower()
        if confirm not in ["s", "sim", "y", "yes"]:
            print("❌ Operação cancelada pelo usuário.")
            sys.exit(1)

    # Obter tipo de versão
    print("\n📈 Tipos de versão disponíveis:")
    print("  1. patch - Correções de bugs (1.0.0 -> 1.0.1)")
    print("  2. minor - Novas funcionalidades (1.0.0 -> 1.1.0)")
    print("  3. major - Mudanças que quebram compatibilidade (1.0.0 -> 2.0.0)")

    while True:
        version_choice = (
            input("\n❓ Escolha o tipo de versão (1-3 ou patch/minor/major): ")
            .lower()
            .strip()
        )

        if version_choice in ["1", "patch"]:
            version_type = "patch"
            break
        elif version_choice in ["2", "minor"]:
            version_type = "minor"
            break
        elif version_choice in ["3", "major"]:
            version_type = "major"
            break
        else:
            print("❌ Opção inválida! Use 1, 2, 3 ou patch, minor, major.")

    # Obter mensagem do commit
    commit_message = input("\n💬 Digite a mensagem do commit: ").strip()
    if not commit_message:
        print("❌ Mensagem do commit não pode estar vazia!")
        sys.exit(1)

    # Mostrar resumo
    current_version = get_current_version()
    print("\n📋 Resumo da operação:")
    print(f"   Versão atual: {current_version}")
    print(f"   Tipo de atualização: {version_type}")
    print(f"   Mensagem do commit: {commit_message}")

    confirm = input("\n❓ Confirma a operação? (S/n): ").lower()
    if confirm in ["n", "no", "não"]:
        print("❌ Operação cancelada pelo usuário.")
        sys.exit(1)

    try:
        # 1. Atualizar versão
        new_version = update_version(version_type)
        # Garante que o arquivo version.txt seja atualizado

        # 2. Adicionar todas as mudanças ao git
        print("📝 Adicionando mudanças ao git...")
        run_command("git add .")

        # 3. Fazer commit
        print("📝 Fazendo commit...")
        full_commit_message = f"{commit_message}\n\nBump version to v{new_version}"
        run_command(f'git commit -m "{full_commit_message}"')

        # 4. Push do commit
        print("📤 Enviando commit para o repositório...")
        run_command("git push origin main")

        # 5. Criar tag
        tag_name = f"v{new_version}"
        print(f"🏷️  Criando tag {tag_name}...")
        run_command(f'git tag "{tag_name}"')

        # 6. Push da tag
        print("📤 Enviando tag para o repositório...")
        run_command(f'git push origin "{tag_name}"')

        # Sucesso!
        print("\n🎉 Release criado com sucesso!")
        print("=" * 40)
        print(f"✅ Versão: {new_version}")
        print(f"✅ Tag: {tag_name}")
        print(f"✅ Commit: {commit_message}")

    except KeyboardInterrupt:
        print("\n❌ Operação cancelada pelo usuário (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
