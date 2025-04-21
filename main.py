# main.py
import subprocess
import sys

def main():
    # Comando para executar o Streamlit com seu script
    command = [
        sys.executable,  # Usa o Python do ambiente
        "-m",
        "streamlit",
        "run",
        "pizza.py",  # Substitua pelo nome do seu arquivo principal
        "--server.port=8501",  # Porta padrão do Streamlit
        "--browser.serverAddress=localhost",
        "--logger.level=error"  # Reduz logs desnecessários
    ]
    
    subprocess.run(command)

if __name__ == "__main__":
    main()