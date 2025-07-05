import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np
import anthropic
import json
import streamlit.components.v1 as components
import os
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import io
import requests
from io import BytesIO
import urllib.request
from soccerplots.radar_chart import Radar
import matplotlib.colors as mcolors
from scipy.stats import pearsonr
import base64
import matplotlib.patheffects as path_effects
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


# Configure page at the very beginning
st.set_page_config(
    page_title="Gerador de Questões Discursivas UERJ",
    page_icon="🎓",  # Generic icon for both subjects
    layout="wide"
)

# Authentication function
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        
        try:
            users = st.secrets["auth"]        
            if (st.session_state["username"] in users and 
                users[st.session_state["username"]] == st.session_state["password"]):
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # Don't store password
                del st.session_state["username"]  # Don't store username
            else:
                st.session_state["password_correct"] = False

        except Exception as e:
            st.error("Erro na configuração de autenticação")
            st.session_state["password_correct"] = False
        
    # Return True if password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.markdown("<h2 style='text-align: center; color: black;'>🔐 Login</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Login", on_click=password_entered)
        
        if st.session_state.get("password_correct", None) == False:
            st.error("😕 Usuário ou senha incorretos")
    
    return False

# Check authentication before showing the app
if not check_password():
    st.stop()  # Stop here if not authenticated
    
st.markdown("<h2 style='text-align: center;  color: black;'>Gerador de Questões Discursivas UERJ<br>2024 </b></h2>", unsafe_allow_html=True)
st.markdown("---")

# Plotting Braileirão Logo
# GitHub raw URL
image_url = "https://raw.githubusercontent.com/JAmerico1898/gerador-questoes-uerj/a3d7bcda0a18dd8e99e577a0aa41c0a42f979d6b/uerj.png"


st.markdown(
    f"""
    <div style="display: flex; justify-content: center;">
        <img src="{image_url}" width="150">
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# Define your options
options = [
    "Química", 
    "Biologia"
    ]

# Create a container for the buttons
st.markdown("<h3 style='text-align: center; color: black;'>Selecione uma opção:</h3>", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'selected_option' not in st.session_state:
    st.session_state.selected_option = None

# Define button click handlers for each option
def select_option(option):
    st.session_state.selected_option = option

# Define custom CSS for button styling
st.markdown("""
<style>
    /* Default button style (light gray) */
    .stButton > button {
        background-color: #f0f2f6 !important;
        color: #31333F !important;
        border-color: #d2d6dd !important;
        width: 100%;
    }
    
    /* Selected button style (red) */
    .selected-button {
        background-color: #FF4B4B !important;
        color: white !important;
        border-color: #FF0000 !important;
        width: 100%;
        padding: 0.5rem;
        font-weight: 400;
        border-radius: 0.25rem;
        cursor: default;
        text-align: center;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Create two rows of columns for the buttons
col1, col2, col3 = st.columns([3, 1, 3])

# Row 1
with col1:
    if st.session_state.selected_option == options[0]:
        # Display selected (red) button
        st.markdown(
            f"""
            <div data-testid="stButton">
                <button class="selected-button">
                    {options[0]}
                </button>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        # Display default (gray) button
        st.button(options[0], key="btn0", use_container_width=True, on_click=select_option, args=(options[0],))

with col3:
    if st.session_state.selected_option == options[1]:
        # Display selected (red) button
        st.markdown(
            f"""
            <div data-testid="stButton">
                <button class="selected-button">
                    {options[1]}
                </button>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        # Display default (gray) button
        st.button(options[1], key="btn1", use_container_width=True, on_click=select_option, args=(options[1],))
        
st.write("---")        

if st.session_state.selected_option == "Química":

    # Configuração da página
    #st.set_page_config(
    #    page_title="Gerador de Questões Discursivas UERJ - Química",
    #    page_icon="🧪",
    #    layout="wide"
    #)

    # Função para inicializar o cliente Anthropic
    @st.cache_resource
    def init_anthropic_client():
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
            return anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            st.error(f"Erro ao inicializar cliente Anthropic: {e}")
            st.error("Verifique se a chave ANTHROPIC_API_KEY está configurada nos secrets do Streamlit.")
            return None

    @st.cache_data
    def carregar_contexto_arquivo(topico_id):
        """Carrega o contexto de um arquivo .txt específico"""
        # Mapeamento de tópico para nome do arquivo
        mapeamento_arquivos = {
            "1.1.1": "1.1.1 - Átomos - partículas subatômicas, configuração eletrônica.txt",
            "1.2.1": "1.2.1 - Elementos químicos - massa atômica, número atômico, isotopia.txt",
            "1.2.2": "1.2.2 - Elementos químicos - classificação periódica e propriedades periódicas.txt",
            "1.3.1": "1.3.1 - Íons e moléculas - ligações químicas.txt",
            "1.3.2": "1.3.2 - Íons e moléculas - geometria molecular.txt",
            "1.3.3": "1.3.3 - Íons e moléculas - interações intermoleculares.txt",
            "1.4.1": "1.4.1 - Bases moleculares da vida - ácidos nucleicos; proteínas; lipídios; carboidratos.txt",
            "2.1.1": "2.1.1 - Substância pura e misturas - conceitos, propriedades, classificações; processos de separação de misturas.txt",
            "2.2.1": "2.2.1 - Soluções - unidades de concentração expressas em percentagem, em g.L-1 e em quantidade de matéria; diluição e misturas.txt",
            "2.3.1": "2.3.1 - Gases ideais - transformações; equação geral dos gases; misturas gasosas.txt",
            "2.4.1": "2.4.1 - Funções químicas - classificação e nomenclatura das substâncias orgânicas e inorgânicas.txt",
            "2.4.2": "2.4.2 - Funções químicas - isomeria.txt",
            "2.5.1": "2.5.1 -  Reações químicas - síntese, decomposição, deslocamento, dupla-troca.txt",
            "2.5.2": "2.5.2 - Reações químicas - balanceamento, ocorrência.txt",
            "2.5.3": "2.5.3 - Reações químicas - oxirredução.txt",
            "2.6.1": "2.6.1 - Cálculo estequiométrico simples - fórmula percentual, mínima e molecular; quantidade de matéria, de massa e de volume nas condições normais.txt",
            "2.7.1": "2.7.1 - Cinética reacional - taxa de reação; fatores de interferência; reações enzimáticas.txt",
            "2.8.1": "2.8.1 - Equilíbrio químico - perturbações; acidez e basicidade.txt",
            "2.9.1": "2.9.1 - Fenômenos térmicos - temperatura, calor, dilatação térmica; calor específico, calor latente, mudanças de estado, calorimetria, termoquímica.txt"
        }
        
        nome_arquivo = mapeamento_arquivos.get(topico_id)
        if nome_arquivo:
            try:
                with open(nome_arquivo, 'r', encoding='utf-8') as file:
                    conteudo = file.read()
                    return conteudo
            except FileNotFoundError:
                st.warning(f"⚠️ Arquivo {nome_arquivo} não encontrado. Usando contexto padrão.")
                return None
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo {nome_arquivo}: {str(e)}")
                return None
        return None

    # Estrutura hierárquica dos temas
    ESTRUTURA_TEMAS = {
        "1.": {
            "titulo": "Os constituintes fundamentais da matéria",
            "subtemas": {
                "1.1": {
                    "titulo": "Átomos: partículas subatômicas; configuração eletrônica",
                    "topicos": {
                        "1.1.1": "Átomos: partículas subatômicas; configuração eletrônica"
                    }
                },
                "1.2": {
                    "titulo": "Elementos químicos: massa atômica, número atômico, isotopia; classificação periódica e propriedades periódicas",
                    "topicos": {
                        "1.2.1": "Elementos químicos: massa atômica, número atômico, isotopia",
                        "1.2.2": "Elementos químicos: classificação periódica e propriedades periódicas"
                    }
                },
                "1.3": {
                    "titulo": "Íons e moléculas: ligações químicas; geometria molecular; interações intermoleculares",
                    "topicos": {
                        "1.3.1": "Íons e moléculas: ligações químicas",
                        "1.3.2": "Íons e moléculas: geometria molecular",
                        "1.3.3": "Íons e moléculas: interações intermoleculares"
                    }
                },
                "1.4": {
                    "titulo": "Bases moleculares da vida: ácidos nucleicos; proteínas; lipídios; carboidratos",
                    "topicos": {
                        "1.4.1": "Bases moleculares da vida: ácidos nucleicos; proteínas; lipídios; carboidratos"
                    }
                }
            }
        },
        "2.": {
            "titulo": "As substâncias e suas transformações",
            "subtemas": {
                "2.1": {
                    "titulo": "Substância pura e misturas: conceitos, propriedades, classificações; processos de separação de misturas",
                    "topicos": {
                        "2.1.1": "Substância pura e misturas: conceitos, propriedades, classificações; processos de separação de misturas"
                    }
                },
                "2.2": {
                    "titulo": "Soluções: unidades de concentração expressas em percentagem, em g.L-1 e em quantidade de matéria; diluição e misturas",
                    "topicos": {
                        "2.2.1": "Soluções: unidades de concentração expressas em percentagem, em g.L-1 e em quantidade de matéria; diluição e misturas"
                    }
                },
                "2.3": {
                    "titulo": "Gases ideais: transformações; equação geral dos gases; misturas gasosas",
                    "topicos": {
                        "2.3.1": "Gases ideais: transformações; equação geral dos gases; misturas gasosas"
                    }
                },
                "2.4": {
                    "titulo": "Funções químicas: classificação e nomenclatura das substâncias orgânicas e inorgânicas; isomeria",
                    "topicos": {
                        "2.4.1": "Funções químicas: classificação e nomenclatura das substâncias orgânicas e inorgânicas",
                        "2.4.2": "Funções químicas: isomeria"
                    }
                },
                "2.5": {
                    "titulo": "Reações químicas: síntese, decomposição, deslocamento, dupla-troca; balanceamento, ocorrência; oxirredução",
                    "topicos": {
                        "2.5.1": "Reações químicas: síntese, decomposição, deslocamento, dupla-troca",
                        "2.5.2": "Reações químicas: balanceamento, ocorrência",
                        "2.5.3": "Reações químicas: oxirredução"
                    }
                },
                "2.6": {
                    "titulo": "Cálculo estequiométrico simples: fórmula percentual, mínima e molecular; quantidade de matéria, de massa e de volume nas condições normais",
                    "topicos": {
                        "2.6.1": "Cálculo estequiométrico simples: fórmula percentual, mínima e molecular; quantidade de matéria, de massa e de volume nas condições normais"
                    }
                },
                "2.7": {
                    "titulo": "Cinética reacional: taxa de reação; fatores de interferência; reações enzimáticas",
                    "topicos": {
                        "2.7.1": "Cinética reacional: taxa de reação; fatores de interferência; reações enzimáticas"
                    }
                },
                "2.8": {
                    "titulo": "Equilíbrio químico: perturbações; acidez e basicidade",
                    "topicos": {
                        "2.8.1": "Equilíbrio químico: perturbações; acidez e basicidade"
                    }
                },
                "2.9": {
                    "titulo": "Fenômenos térmicos: temperatura, calor, dilatação térmica; calor específico, calor latente, mudanças de estado, calorimetria, termoquímica",
                    "topicos": {
                        "2.9.1": "Fenômenos térmicos: temperatura, calor, dilatação térmica; calor específico, calor latente, mudanças de estado, calorimetria, termoquímica"
                    }
                }
            }
        }
    }

    # Contextos específicos para os tópicos disponíveis
    CONTEXTOS_TOPICOS = {
        "1.1.1": """
    ## CONTEXTO: Átomos - partículas subatômicas; configuração eletrônica (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Prótons, nêutrons e elétrons - identificação e cálculos
    - Estrutura nuclear e suas propriedades
    - Número atômico e número de massa - relações e aplicações
    - Isótopos e suas propriedades específicas
    - Radioatividade e processos de decaimento nuclear
    - Partículas subatômicas em reações nucleares
    - Distribuição eletrônica em subníveis (s, p, d, f) com justificativas
    - Configuração eletrônica fundamental e excitada - comparações
    - Ordem energética dos orbitais - explicações teóricas
    - Configuração baseada em gás nobre - vantagens e aplicações
    - Camadas eletrônicas (K, L, M, N, O, P, Q) - determinação e análise
    - Elétrons de valência - identificação e importância química

    Exemplos de questões discursivas incluem:
    - Aluminotermia e configuração eletrônica do vanádio
    - Fusão nuclear e isótopos do hidrogênio
    - Síntese de elementos superpesados
    - Decaimento radioativo e transmutação nuclear
    - Estrutura nuclear e partículas subatômicas
    - Determinação completa da configuração eletrônica com justificativas
    - Identificação e explicação do subnível de maior energia
    - Cálculo e análise do número de camadas eletrônicas
    """,
        "1.2.1": """
    ## CONTEXTO: Elementos químicos - massa atômica, número atômico, isotopia (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Número atômico (Z) e número de massa (A) - definições e aplicações
    - Conceito de isótopos - semelhanças e diferenças detalhadas
    - Notação isotópica (A_Z X) - interpretação e uso
    - Cálculos complexos com isótopos e justificativas
    - Aplicações dos isótopos (datação, medicina nuclear) com análises
    - Abundância isotópica - cálculos e significado
    - Decaimento radioativo e meia-vida
    - Elementos artificiais e transmutação nuclear

    Exemplos de questões discursivas incluem:
    - Elementos essenciais ao organismo e isótopos predominantes
    - Decaimento radioativo de radioisótopos (radônio, carbono-14)
    - Síntese de elementos superpesados em aceleradores
    - Análise de isótopos do hidrogênio na fusão nuclear
    - Cálculos de meia-vida e cinética de decaimento
    - Aplicações médicas e arqueológicas de isótopos
    """,
        "1.2.2": """
    ## CONTEXTO: Elementos químicos - classificação periódica e propriedades periódicas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Organização da tabela periódica (grupos e períodos) - análise histórica
    - Famílias químicas (metais alcalinos, alcalino terrosos, halogênios, gases nobres)
    - Propriedades periódicas: raio atômico, energia de ionização, eletronegatividade
    - Evolução histórica da tabela periódica - Mendeleiev vs. atual
    - Metais, ametais e semimetais - classificação e propriedades
    - Propriedades dos elementos e suas aplicações práticas
    - Tendências nos grupos e períodos
    - Anomalias na classificação periódica

    Exemplos de questões discursivas incluem:
    - Tabela de Mendeleiev e classificação atual (Te-I)
    - Metais de transição e propriedades (meteorito do Bendegó)
    - Síntese de elementos superpesados e grupos da tabela
    - Regra do octeto e estabilidade eletrônica
    - Símbolos químicos e propriedades periódicas
    - Metais das medalhas olímpicas e suas propriedades
    - Minerais carbonatados e raio atômico
    """,
        "1.3.1": """
    ## CONTEXTO: Íons e moléculas - ligações químicas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Ligações químicas: iônica, covalente e metálica - características e diferenças
    - Formação de compostos iônicos e moleculares - mecanismos e justificativas
    - Polaridade de ligações químicas - diferença de eletronegatividade
    - Estados de oxidação e sua determinação em compostos
    - Propriedades dos compostos relacionadas ao tipo de ligação
    - Fórmulas químicas e estruturais de compostos iônicos e moleculares
    - Energia de ligação e estabilidade de compostos

    Exemplos de questões discursivas incluem:
    - Ciclo do nitrogênio e fixação biológica
    - Garimpo ilegal e ligação metálica (amálgama Hg-Au)
    - Baterias de sal fundido e ligação iônica
    - Regra do octeto e formação de fluoreto de sódio
    - Carbonato de magnésio e ligações químicas
    - Dióxido de zircônio e ligação iônica
    - Meteorito do Bendegó e ligação metálica
    """,
        "1.3.2": """
    ## CONTEXTO: Íons e moléculas - geometria molecular (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Teoria VSEPR (repulsão dos pares eletrônicos) - aplicação e previsões
    - Geometrias moleculares: linear, angular, trigonal plana, tetraédrica, piramidal
    - Polaridade molecular - momento dipolar e sua determinação
    - Relação entre geometria molecular e propriedades físicas
    - Hibridização de orbitais atômicos - tipos e características
    - Influência da geometria nas propriedades químicas e biológicas
    - Ângulos de ligação e justificativas teóricas

    Exemplos de questões discursivas incluem:
    - Gases do efeito estufa e geometria molecular (CO₂, CH₄, N₂O, O₃)
    - Síntese industrial de amônia e geometria piramidal
    - Símbolos químicos e geometria molecular (metano)
    - Óxidos de enxofre e geometria molecular
    - Síntese eletrocatalítica e fórmulas estruturais
    - Processo industrial e geometria do metanal
    - Anabolizantes e geometria molecular
    """,
        "1.3.3": """
    ## CONTEXTO: Íons e moléculas - interações intermoleculares (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Forças intermoleculares: van der Waals, dipolo-dipolo, ligações de hidrogênio
    - Relação entre forças intermoleculares e propriedades físicas
    - Pontos de ebulição e fusão - influência das interações moleculares
    - Solubilidade e miscibilidade - princípio "semelhante dissolve semelhante"
    - Tensão superficial e viscosidade - explicações moleculares
    - Estruturas cristalinas e empacotamento molecular
    - Propriedades coligativas e interações

    Exemplos de questões discursivas incluem:
    - Isomeria plana e propriedades físicas (pentanos)
    - Processo industrial e propriedades coligativas
    - Soluções de ácido clorídrico e ligações de hidrogênio
    - Óxidos de enxofre e solubilidade
    - Poder oxidante e polaridade molecular
    - Temperaturas de ebulição e ramificação molecular
    """,
        "1.4.1": """
    ## CONTEXTO: Bases moleculares da vida - ácidos nucleicos; proteínas; lipídios; carboidratos (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Estrutura e função dos ácidos nucleicos (DNA, RNA)
    - Aminoácidos e estrutura das proteínas
    - Classificação e propriedades dos lipídios
    - Monossacarídeos, dissacarídeos e polissacarídeos
    - Funções biológicas das biomoléculas
    - Metabolismo e processos bioquímicos
    - Relação estrutura-função nas biomoléculas

    Exemplos de questões discursivas incluem:
    - Estrutura do DNA e replicação
    - Síntese proteica e código genético
    - Metabolismo de carboidratos
    - Função dos lipídios nas membranas
    - Enzimas e catálise biológica
    """,
        "2.1.1": """
    ## CONTEXTO: Substância pura e misturas - conceitos, propriedades, classificações; processos de separação de misturas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Substâncias puras vs. misturas homogêneas e heterogêneas
    - Propriedades físicas e químicas
    - Métodos de separação: filtração, destilação, cristalização
    - Processos de purificação
    - Critérios de pureza
    - Aplicações industriais dos métodos de separação

    Exemplos de questões discursivas incluem:
    - Separação de componentes em misturas
    - Destilação fracionada de petróleo
    - Purificação de substâncias
    - Análise de pureza de reagentes
    """,
        "2.2.1": """
    ## CONTEXTO: Soluções - unidades de concentração expressas em percentagem, em g.L-1 e em quantidade de matéria; diluição e misturas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Concentração em percentagem, g/L e mol/L
    - Cálculos de diluição e mistura de soluções
    - Propriedades das soluções
    - Solubilidade e fatores que a influenciam
    - Curvas de solubilidade
    - Soluções saturadas, insaturadas e supersaturadas

    Exemplos de questões discursivas incluem:
    - Cálculos de concentração molar
    - Diluição de ácidos concentrados
    - Mistura de soluções com diferentes concentrações
    - Análise de solubilidade de compostos
    """,
        "2.3.1": """
    ## CONTEXTO: Gases ideais - transformações; equação geral dos gases; misturas gasosas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Leis dos gases ideais (Boyle, Charles, Gay-Lussac)
    - Equação geral dos gases (PV = nRT)
    - Transformações gasosas isotérmicas, isobáricas e isocóricas
    - Misturas gasosas e pressões parciais
    - Lei de Dalton das pressões parciais
    - Densidade dos gases e massa molar

    Exemplos de questões discursivas incluem:
    - Transformações de gases em diferentes condições
    - Cálculos com a equação geral dos gases
    - Misturas gasosas na atmosfera
    - Aplicações industriais dos gases
    """,
        "2.4.1": """
    ## CONTEXTO: Funções químicas - classificação e nomenclatura das substâncias orgânicas e inorgânicas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Funções inorgânicas: ácidos, bases, sais e óxidos
    - Funções orgânicas: hidrocarbonetos, álcoois, aldeídos, cetonas, ácidos carboxílicos
    - Nomenclatura IUPAC e usual
    - Propriedades químicas das diferentes funções
    - Aplicações práticas dos compostos
    - Identificação de grupos funcionais

    Exemplos de questões discursivas incluem:
    - Nomenclatura de compostos orgânicos e inorgânicos
    - Classificação de óxidos (neutros, ácidos, básicos)
    - Identificação de funções em moléculas complexas
    - Propriedades relacionadas aos grupos funcionais
    """,
        "2.4.2": """
    ## CONTEXTO: Funções químicas - isomeria (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Isomeria plana: cadeia, posição, função, compensação
    - Isomeria espacial: óptica e geométrica
    - Carbonos assimétricos e atividade óptica
    - Propriedades físicas de isômeros
    - Relação entre isomeria e atividade biológica
    - Aplicações farmacológicas da isomeria

    Exemplos de questões discursivas incluem:
    - Isômeros planos de pentanos e propriedades físicas
    - Carbonos assimétricos em fármacos
    - Isomeria óptica e atividade biológica
    - Síntese orgânica e mecanismos reacionais
    """,
        "2.5.1": """
    ## CONTEXTO: Reações químicas - síntese, decomposição, deslocamento, dupla-troca (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Tipos de reações químicas e suas características
    - Reações de síntese (combinação)
    - Reações de decomposição (análise)
    - Reações de deslocamento (simples troca)
    - Reações de dupla-troca (metátese)
    - Previsão de produtos de reação
    - Condições reacionais

    Exemplos de questões discursivas incluem:
    - Classificação de reações químicas
    - Previsão de produtos em diferentes tipos de reação
    - Aplicações industriais das reações
    - Mecanismos de reação
    """,
        "2.5.2": """
    ## CONTEXTO: Reações químicas - balanceamento, ocorrência (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Balanceamento de equações químicas
    - Lei da conservação da massa
    - Condições para ocorrência de reações
    - Fatores que influenciam a velocidade de reação
    - Energia de ativação
    - Catalisadores e inibidores

    Exemplos de questões discursivas incluem:
    - Balanceamento de equações complexas
    - Análise de condições reacionais
    - Fatores que favorecem ou desfavorecem reações
    - Papel dos catalisadores
    """,
        "2.5.3": """
    ## CONTEXTO: Reações químicas - oxirredução (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Conceitos de oxidação e redução
    - Número de oxidação (NOX)
    - Agentes oxidantes e redutores
    - Balanceamento de equações redox
    - Células eletroquímicas e eletrólise
    - Potenciais de redução
    - Aplicações da eletroquímica

    Exemplos de questões discursivas incluem:
    - Aluminotermia e agentes redutores
    - Reações redox e pureza de reagentes
    - Baterias e células eletrolíticas
    - Eletrólise em série
    - Poder oxidante e potenciais eletroquímicos
    """,
        "2.6.1": """
    ## CONTEXTO: Cálculo estequiométrico simples - fórmula percentual, mínima e molecular; quantidade de matéria, de massa e de volume nas condições normais (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Fórmulas químicas: percentual, mínima e molecular
    - Conceito de mol e quantidade de matéria
    - Massa molar e constante de Avogadro
    - Volume molar nas CNTP
    - Cálculos estequiométricos simples
    - Rendimento de reações
    - Pureza de reagentes

    Exemplos de questões discursivas incluem:
    - Determinação de fórmulas moleculares
    - Cálculos com quantidade de matéria
    - Estequiometria com pureza de reagentes
    - Rendimento teórico vs. real
    """,
        "2.7.1": """
    ## CONTEXTO: Cinética reacional - taxa de reação; fatores de interferência; reações enzimáticas (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Velocidade de reação e fatores que a influenciam
    - Teoria das colisões e energia de ativação
    - Catálise homogênea e heterogênea
    - Enzimas como catalisadores biológicos
    - Mecanismos de reação
    - Ordem de reação e leis de velocidade

    Exemplos de questões discursivas incluem:
    - Fatores que afetam a velocidade de reação
    - Mecanismo de ação das enzimas
    - Efeito da temperatura e concentração
    - Catálise industrial
    """,
        "2.8.1": """
    ## CONTEXTO: Equilíbrio químico - perturbações; acidez e basicidade (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Conceito de equilíbrio químico
    - Princípio de Le Chatelier
    - Constante de equilíbrio (Kc, Kp)
    - Fatores que deslocam o equilíbrio
    - Teorias ácido-base (Arrhenius, Brønsted-Lowry, Lewis)
    - pH, pOH e força de ácidos e bases
    - Hidrólise de sais

    Exemplos de questões discursivas incluem:
    - Síntese industrial de amônia (processo Haber)
    - Efeito de temperatura e pressão no equilíbrio
    - Cálculos de pH e pOH
    - Teoria ácido-base de Lewis
    """,
        "2.9.1": """
    ## CONTEXTO: Fenômenos térmicos - temperatura, calor, dilatação térmica; calor específico, calor latente, mudanças de estado, calorimetria, termoquímica (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Conceitos de temperatura e calor
    - Dilatação térmica de sólidos, líquidos e gases
    - Calor específico e capacidade calorífica
    - Calor latente e mudanças de estado
    - Calorimetria e balanço térmico
    - Termoquímica: entalpia, calor de formação, combustão
    - Leis da termodinâmica

    Exemplos de questões discursivas incluem:
    - Cálculos de dilatação térmica
    - Calorimetria e balanço energético
    - Entalpias de reação
    - Mudanças de estado e energia
    """
    }

    def get_contexto_completo(topico_id):
        """Retorna o contexto completo para um tópico específico"""
        # Primeiro tenta carregar do arquivo .txt
        contexto_arquivo = carregar_contexto_arquivo(topico_id)
        
        if contexto_arquivo:
            # Se arquivo foi carregado com sucesso, usa seu conteúdo
            return contexto_arquivo
        else:
            # Fallback para contexto hardcoded se arquivo não existir
            contexto_base = CONTEXTOS_TOPICOS.get(topico_id, "")
            
            # Adiciona exemplos de questões baseados nos documentos fornecidos
            if topico_id in ["1.1.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Aluminotermia e configuração eletrônica do vanádio
    - Fusão nuclear e isótopos do hidrogênio
    - Síntese de elementos superpesados
    - Decaimento radioativo e transmutação nuclear
    - Estrutura nuclear e partículas subatômicas
    """
            elif topico_id in ["1.2.1", "1.2.2"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Propriedades periódicas e elementos essenciais
    - Tabela de Mendeleiev vs. classificação atual
    - Metais de transição e suas propriedades
    - Famílias químicas e formação de compostos
    - Síntese de elementos superpesados
    """
            elif topico_id in ["1.3.1", "1.3.2", "1.3.3"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Ciclo do nitrogênio e ligações químicas
    - Garimpo ilegal e propriedades dos metais
    - Isomeria plana e propriedades físicas
    - Gases do efeito estufa e geometria molecular
    - Reações redox e polaridade molecular
    - Baterias de sal fundido e eletroquímica
    """
            elif topico_id in ["2.5.3"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Aluminotermia e agentes redutores
    - Eletrólise em série com células eletrolíticas
    - Poder oxidante de hipoclorito e ozônio
    - Baterias e potenciais eletroquímicos
    """
            
            return contexto_base


    def gerar_questao(client, tema, subtema, topico, num_questoes, dificuldade):
        """Gera questões discursivas usando a API do Claude"""
        
        contexto_topico = get_contexto_completo(topico.split(' ', 1)[0] if ' ' in topico else topico)
        
        prompt = f"""
    Como professor experiente de Química da UERJ, elabore EXATAMENTE {num_questoes} questão(ões) discursiva(s) original(is) sobre o tópico:

    **TEMA:** {tema}
    **SUBTEMA:** {subtema}  
    **TÓPICO:** {topico}

    **CONTEXTO DO TÓPICO:**
    {contexto_topico}

    **INSTRUÇÕES ESPECÍFICAS:**
    1. Crie APENAS questões DISCURSIVAS no estilo UERJ (contextualizada, interdisciplinar quando possível)
    2. Dificuldade: {dificuldade}
    3. Inclua dados necessários, tabelas ou gráficos quando apropriado
    4. As questões devem ser claras, bem estruturadas e desafiadoras
    5. NÃO use alternativas de múltipla escolha - apenas questões abertas
    6. Use contextos reais e aplicações práticas
    7. Inclua cálculos quando necessário
    8. Mantenha consistência com o padrão UERJ de questões discursivas

    **CARACTERÍSTICAS DAS QUESTÕES DISCURSIVAS UERJ:**
    - Contextualização com situações reais e atuais
    - Interdisciplinaridade quando possível
    - Múltiplas habilidades em uma questão
    - Dados experimentais ou situações práticas
    - Aplicação de conceitos teóricos em contextos reais
    - Respostas que exigem desenvolvimento, explicação e justificativa
    - Questões que avaliam capacidade de análise e síntese

    **FORMATO OBRIGATÓRIO DE RESPOSTA:**
    Para cada questão, forneça EXATAMENTE:

    """ + "\n".join([f"""
    ### QUESTÃO {i}
    [Enunciado completo com contexto rico e situação real]

    [Dados, tabelas ou informações complementares se necessário]

    **O que se pede:**
    a) [Primeira pergunta discursiva]
    b) [Segunda pergunta discursiva]
    c) [Terceira pergunta discursiva - se aplicável]""" for i in range(1, num_questoes + 1)]) + f"""

    """ + "\n".join([f"""
    ### GABARITO E SOLUÇÃO DETALHADA {i}
    **Solução completa:**

    **Item a)**
    [Resposta esperada detalhada]
    [Desenvolvimento passo a passo]
    [Cálculos quando necessário]

    **Item b)**
    [Resposta esperada detalhada]
    [Desenvolvimento passo a passo]
    [Justificativas teóricas]

    **Item c)** (se aplicável)
    [Resposta esperada detalhada]
    [Explicações conceituais]

    **Conceitos envolvidos:**
    - [conceito químico 1]
    - [conceito químico 2]
    - [conceito químico 3]
    - [aplicações práticas]""" for i in range(1, num_questoes + 1)]) + f"""

    ---

    IMPORTANTE: Gere EXATAMENTE {num_questoes} questão(ões) discursiva(s) agora, seguindo rigorosamente este formato. NÃO inclua alternativas de múltipla escolha."""


        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            st.error(f"Erro detalhado: {str(e)}")
            return f"❌ **Erro ao gerar questão**\n\nDetalhes técnicos: {str(e)}\n\nVerifique:\n- Conexão com internet\n- Validade da chave API\n- Configuração dos secrets"

    def main():
        st.title("🧪 Gerador de Questões Discursivas UERJ - Química")
        st.markdown("*Sistema inteligente para criação de questões discursivas de vestibular baseado no padrão UERJ*")

        # ADICIONAR ESTA PARTE - Sistema de navegação
        tab1, tab2 = st.tabs(["🚀 Gerador de Questões", "📊 Análise Estatística"])
        
        with tab1:
            # TODO O CÓDIGO EXISTENTE DA FUNÇÃO main() DEVE FICAR AQUI (indentado)
            # Mover todo o resto do código da função main() para dentro desta aba
            
            # Inicializar cliente
            client = init_anthropic_client()
            if not client:
                st.stop()
            
            # CSS personalizado para melhorar aparência
            st.markdown("""
            <style>
            .stSelectbox > div > div > select {
                background-color: #f0f2f6;
            }
            .success-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                margin: 1rem 0;
            }
            .info-card {
                padding: 1.5rem;
                border-radius: 0.5rem;
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                margin: 1rem 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Sidebar para seleção
            st.sidebar.header("⚙️ Configurações")
            
            # Seleção do tema
            temas_opcoes = {f"{k} {v['titulo']}": k for k, v in ESTRUTURA_TEMAS.items()}
            tema_selecionado = st.sidebar.selectbox(
                "📚 Selecione o Tema:",
                list(temas_opcoes.keys()),
                help="Escolha o tema principal do conteúdo"
            )
            tema_id = temas_opcoes[tema_selecionado]
            
            # Seleção do subtema
            subtemas_disponiveis = ESTRUTURA_TEMAS[tema_id]["subtemas"]
            subtemas_opcoes = {f"{k} {v['titulo']}": k for k, v in subtemas_disponiveis.items()}
            subtema_selecionado = st.sidebar.selectbox(
                "📖 Selecione o Subtema:",
                list(subtemas_opcoes.keys()),
                help="Escolha o subtema específico"
            )
            subtema_id = subtemas_opcoes[subtema_selecionado]
            
            # Seleção do tópico
            topicos_disponiveis = subtemas_disponiveis[subtema_id]["topicos"]
            if topicos_disponiveis:
                topicos_opcoes = {f"{k} {v}": k for k, v in topicos_disponiveis.items()}
                topico_selecionado = st.sidebar.selectbox(
                    "📝 Selecione o Tópico:",
                    list(topicos_opcoes.keys()),
                    help="Escolha o tópico específico para a questão"
                )
                topico_id = topicos_opcoes[topico_selecionado]
                contexto_disponivel = topico_id in CONTEXTOS_TOPICOS
            else:
                st.sidebar.warning("⚠️ Este subtema não possui tópicos específicos disponíveis.")
                topico_selecionado = subtema_selecionado
                topico_id = subtema_id
                contexto_disponivel = False
            
            # Indicador de contexto disponível
            if contexto_disponivel:
                # Verificar se o contexto vem de arquivo ou é hardcoded
                contexto_arquivo = carregar_contexto_arquivo(topico_id)
                if contexto_arquivo:
                    st.sidebar.success("✅ Contexto especializado carregado do arquivo")
                else:
                    st.sidebar.success("✅ Contexto especializado disponível")
            else:
                st.sidebar.info("ℹ️ Usando contexto geral do subtema")
                    
            # Configurações adicionais
            #st.sidebar.markdown("---")
            st.sidebar.markdown("### 🎛️ Parâmetros de Geração")
            
            # Seleção do número de questões
            #st.sidebar.markdown("---")
            num_questoes = st.sidebar.slider("🔢 Número de questões:", 1, 5, 1)
            dificuldade = st.sidebar.selectbox(
                "📊 Nível de dificuldade:",
                ["fácil", "média", "difícil"]
            )
                
            # Configurações avançadas
            with st.sidebar.expander("🔧 Características das Questões"):
                st.markdown("""
                ✅ **Formato:** Apenas questões discursivas  
                ✅ **Estrutura:** Contexto + múltiplos itens  
                ✅ **Estilo:** Padrão UERJ contextualizado  
                ✅ **Quantidade:** Entre 1 e 5: o usuário escolhe  
                ✅ **Cálculos:** Incluídos quando necessário  
                ✅ **Interdisciplinar:** Quando aplicável  
                """)
            
            # Botão para gerar questões
            texto_botao = f"🚀 Gerar {num_questoes} Questão{'s' if num_questoes > 1 else ''} Discursiva{'s' if num_questoes > 1 else ''}"
            gerar_button = st.sidebar.button(texto_botao, type="primary", use_container_width=True)
                
            if gerar_button:
                # Validações
                if not client:
                    st.error("❌ Cliente Anthropic não inicializado. Verifique a configuração da API key.")
                    return
                    
                # Mostrar informações da seleção
                st.markdown("### 📋 Questões Sendo Geradas:")
                
                # Verificar fonte do contexto
                contexto_arquivo = carregar_contexto_arquivo(topico_id) if contexto_disponivel else None
                fonte_contexto = "Arquivo especializado" if contexto_arquivo else ("Especializado" if contexto_disponivel else "Geral")
                
                st.markdown(f"""
                <div class="info-card">
                <strong>📚 Tema:</strong> {tema_selecionado}<br>
                <strong>📖 Subtema:</strong> {subtema_selecionado}<br>
                <strong>📝 Tópico:</strong> {topico_selecionado}<br>
                <strong>📊 Dificuldade:</strong> {dificuldade.title()}<br>
                <strong>🎯 Contexto:</strong> {fonte_contexto}<br>
                <strong>📁 Fonte:</strong> {'Arquivo .txt' if contexto_arquivo else 'Código interno'}
                <strong>🔢 Quantidade:</strong> {num_questoes} questão{'ões' if num_questoes > 1 else ''} discursiva{'s' if num_questoes > 1 else ''}<br>
                </div>
                """, unsafe_allow_html=True)
                        
                # Progresso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("🔄 Gerando questões... Por favor, aguarde."):
                    status_text.text("🤖 Conectando com IA...")
                    progress_bar.progress(25)
                    
                    status_text.text(f"📝 Elaborando {num_questoes} questão{'ões' if num_questoes > 1 else ''} discursiva{'s' if num_questoes > 1 else ''}...")

                    progress_bar.progress(50)
                    
                    resultado = gerar_questao(
                        client, 
                        tema_selecionado, 
                        subtema_selecionado, 
                        topico_selecionado,
                        num_questoes,
                        dificuldade
                    )
                    
                    status_text.text("✅ Processando resultado...")
                    progress_bar.progress(75)
                    
                    progress_bar.progress(100)
                    status_text.text(f"🎉 {num_questoes} questão{'ões' if num_questoes > 1 else ''} gerada{'s' if num_questoes > 1 else ''} com sucesso!")

                
                # Limpar elementos de progresso após um delay
                import time
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
                # Verificar se houve erro
                if resultado.startswith("❌"):
                    st.error(resultado)
                    return
                
                # Exibir resultado
                st.markdown("---")
                st.markdown("## 📋 Questões Geradas")
                
                # Dividir o resultado em questões e gabaritos
                partes = resultado.split("### GABARITO E SOLUÇÃO DETALHADA")
                
                if len(partes) > 1:
                    # Exibir questões
                    questoes_parte = partes[0]
                    st.markdown(questoes_parte)
                    
                    # Botão para download das questões (futuro)
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        st.markdown("""
                        <div class="success-box">
                        ✅ Questões geradas com sucesso! Use os expanders abaixo para ver as soluções.
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Exibir gabaritos em expanders
                    st.markdown("---")
                    st.markdown("## 🔑 Gabaritos e Soluções Detalhadas")
                    st.markdown("*Clique nos cards abaixo para visualizar as soluções completas*")
                    
                    for i in range(1, len(partes)):
                        gabarito_parte = "### GABARITO E SOLUÇÃO DETALHADA" + partes[i]
                        
                        # Extrair número da questão para o título do expander
                        linhas = gabarito_parte.split('\n')
                        titulo_questao = linhas[0].replace("### GABARITO E SOLUÇÃO DETALHADA", "Solução da Questão") if linhas else f"Solução da Questão {i}"
                        
                        with st.expander(f"💡 {titulo_questao}", expanded=False):
                            st.markdown(gabarito_parte)
                            
                            # Botões de ação para cada solução
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button(f"📋 Copiar Questão {i}", key=f"copy_{i}"):
                                    st.success("Funcionalidade de cópia será implementada!")
                            with col2:
                                if st.button(f"⭐ Favoritar {i}", key=f"fav_{i}"):
                                    st.success("Questão favoritada!")
                else:
                    # Se não conseguiu dividir, exibir tudo
                    st.markdown(resultado)
                    
                # Feedback do usuário
                st.markdown("---")
                st.markdown("### 📝 Feedback")
                col1, col2 = st.columns([1, 1])
                with col1:
                    rating = st.selectbox("Avalie a qualidade das questões:", 
                                        ["Selecione...", "⭐ Ruim", "⭐⭐ Regular", "⭐⭐⭐ Bom", "⭐⭐⭐⭐ Muito Bom", "⭐⭐⭐⭐⭐ Excelente"])
                with col2:
                    if st.button("📤 Enviar Feedback"):
                        if rating != "Selecione...":
                            st.success("Obrigado pelo feedback!")
                        else:
                            st.warning("Por favor, selecione uma avaliação.")
            
            # Informações adicionais na sidebar
            st.sidebar.markdown("---")
            st.sidebar.markdown("### ℹ️ Informações do Sistema")
            st.sidebar.info(
                "🤖 **IA:** Claude Sonnet 4\n\n"
                "📊 **Base:** Questões UERJ reais\n\n"
                "📝 **Formato:** Apenas discursivas\n\n"
                "🔢 **Quantidade:** 1-5 questões/geração\n\n"
                "✅ **Status:** Operacional"
            )
            
            # Estatísticas na sidebar
            with st.sidebar.expander("📈 Estatísticas"):
                st.markdown("""
                **Temas disponíveis:** 2  
                **Subtemas:** 9  
                **Tópicos específicos:** 20  
                **Contextos detalhados:** 19  
                **Formato:** Questões discursivas apenas
                **Questões por geração:** 1-5 (configurável)
                
                **Última atualização:** Dezembro 2024
                """)
                    
            # Área principal com informações quando nenhuma questão foi gerada
            if not gerar_button:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("""
                    ### 🎯 Como usar este sistema:
                    
                    1. **📚 Selecione o tema** na barra lateral
                    2. **📖 Escolha o subtema** relacionado
                    3. **📝 Escolha o tópico específico** (quando disponível)
                    4. **⚙️ Configure** o número de questões e dificuldade
                    5. **🚀 Clique em "Gerar Questões"** para criar as questões
                    
                    ### 🔬 Todos os Tópicos com contexto especializado:
                    - ✅ **Tema 1:** 6 tópicos com contexto completo
                    - ✅ **Tema 2:** 13 tópicos com contexto completo
                    - 📁 **Fonte:** Arquivos .txt com questões dos vestibulares de 2013 a 2025
                    
                    ### 📊 Recursos do sistema:
                    - ✅ Questões contextualizadas no estilo UERJ
                    - ✅ Gabaritos com soluções detalhadas passo a passo
                    - ✅ Múltiplos níveis de dificuldade
                    - ✅ Baseado em questões reais de vestibulares
                    - ✅ Interface intuitiva e responsiva
                    - ✅ Sistema de feedback integrado
                    """)
                
                with col2:
                    st.markdown("""
                    ### 📈 Visão Geral dos Conteúdos:
                    
                    **🧬 Tema 1 - Constituintes da matéria:**
                    - 4 subtemas principais
                    - 6 tópicos específicos
                    - Foco em estrutura atômica
                    
                    **⚗️ Tema 2 - Substâncias e transformações:**
                    - 9 subtemas principais  
                    - 14 tópicos específicos
                    - Foco em reações e processos
                                
                    ### 🔧 Tecnologia:
                    - 🤖 Claude Sonnet 4 (Anthropic)
                    - 🐍 Python + Streamlit
                    - 📊 Interface responsiva
                    - 🔒 API keys protegidas
                    """)
                    
            # Inicializar cliente
            client = init_anthropic_client()
            if not client:
                st.stop()
            
            # Informações adicionais
            st.sidebar.markdown("---")
            st.sidebar.markdown("### ℹ️ Informações")
            st.sidebar.info(
                "Este gerador utiliza inteligência artificial para criar questões "
                "baseadas no padrão e contexto das provas da UERJ. "
                "As questões são geradas com base nos tópicos selecionados."
            )
        
        with tab2:
            exibir_graficos()
            return  # Importante: return aqui para não executar o resto da função

    def exibir_graficos():
        """Exibe página com gráficos interativos de análise das questões UERJ"""
        st.title("📊 Análise Estatística - Questões de Química UERJ")
        st.markdown("*Visualização interativa da evolução dos temas ao longo dos anos (2013-2025)*")
        
        # Carregar dados CSV no Python
        try:
            df = pd.read_csv('gráficos.csv')
            st.success("✅ Arquivo de dados carregado com sucesso!")
            
            # Converter dados para JSON para passar ao JavaScript
            dados_json = df.to_json(orient='records')
            
            # Embed do gráfico HTML com dados embutidos
            components.html(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Análise de Questões de Química UERJ</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .title {{
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }}
            .controls {{
                margin-bottom: 20px;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }}
            .control-group {{
                margin-bottom: 15px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #495057;
            }}
            select {{
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }}
            .chart-container {{
                width: 100%;
                height: 600px;
                margin-top: 20px;
            }}
            .info-box {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
            }}
            .filter-options {{
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }}
            .filter-options > div {{
                flex: 1;
                min-width: 200px;
            }}
            .metrics {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            .metric-card {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                flex: 1;
                min-width: 150px;
                text-align: center;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-label {{
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="title">Análise de Questões de Química - UERJ (2013-2025)</h1>
            
            <div class="info-box">
                <strong>Como usar:</strong> Selecione um tema, subtema ou tópico específico para visualizar sua evolução ao longo dos anos. 
                Passe o mouse sobre os pontos do gráfico para ver informações detalhadas.
            </div>

            <div class="controls">
                <div class="filter-options">
                    <div class="control-group">
                        <label for="tipoSelect">Tipo:</label>
                        <select id="tipoSelect">
                            <option value="">Todos</option>
                            <option value="Tema">Tema</option>
                            <option value="Sub-tema">Sub-tema</option>
                            <option value="Tópico">Tópico</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label for="itemSelect">Item:</label>
                        <select id="itemSelect">
                            <option value="">Selecione um item</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="metrics" id="metricsContainer" style="display: none;">
                <div class="metric-card">
                    <div class="metric-value" id="totalQuestoes">0</div>
                    <div class="metric-label">Total de Questões</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="participacaoTotal">0%</div>
                    <div class="metric-label">Participação Total</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="mediaAnual">0</div>
                    <div class="metric-label">Média Anual</div>
                </div>
            </div>

            <div class="chart-container" id="chartContainer"></div>
        </div>

        <script>
            // Dados carregados do Python
            const data = {dados_json};
            let totalQuestoesPorAno = {{}};

            // Função para processar dados
            function processData() {{
                try {{
                    // Calcular total de questões por ano
                    const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                    anos.forEach(ano => {{
                        totalQuestoesPorAno[ano] = data.reduce((sum, row) => sum + (row[ano] || 0), 0);
                    }});

            // ADIÇÃO: Calcular totais por tipo e ano para participação percentual correta
            window.totaisPorTipoEAno = {{}};
            anos.forEach(ano => {{
                window.totaisPorTipoEAno[ano] = {{
                    'Tema': data.filter(row => row['Tema/Subtema/Tópico'] === 'Tema')
                            .reduce((sum, row) => sum + (row[ano] || 0), 0),
                    'Sub-tema': data.filter(row => row['Tema/Subtema/Tópico'] === 'Sub-tema')
                                .reduce((sum, row) => sum + (row[ano] || 0), 0),
                    'Tópico': data.filter(row => row['Tema/Subtema/Tópico'] === 'Tópico')
                                .reduce((sum, row) => sum + (row[ano] || 0), 0)
                }};
            }});

                    populateFilters();
                    
                }} catch (error) {{
                    console.error('Erro ao processar dados:', error);
                    document.getElementById('chartContainer').innerHTML = '<p style="text-align: center; color: red;">Erro ao processar os dados.</p>';
                }}
            }}

            // Função para popular os filtros
            function populateFilters() {{
                const tipoSelect = document.getElementById('tipoSelect');
                const itemSelect = document.getElementById('itemSelect');

                // Debug: verificar estrutura dos dados
                console.log('Dados carregados:', data);
                console.log('Primeira linha:', data[0]);

                // Limpar opções anteriores
                itemSelect.innerHTML = '<option value="">Selecione um item</option>';

                // Listener para mudança de tipo
                tipoSelect.addEventListener('change', function() {{
                    const tipoSelecionado = this.value;
                    console.log('Tipo selecionado:', tipoSelecionado);
                    
                    itemSelect.innerHTML = '<option value="">Selecione um item</option>';

                    if (tipoSelecionado) {{
                        const itensFiltrados = data.filter(row => row['Tema/Subtema/Tópico'] === tipoSelecionado);
                        console.log('Itens filtrados:', itensFiltrados);
                        
                        itensFiltrados.forEach(item => {{
                            const option = document.createElement('option');
                            option.value = item['Índice'];
                            option.textContent = item['Título'];
                            itemSelect.appendChild(option);
                        }});
                    }} else {{
                        // Mostrar todos os itens
                        data.forEach(item => {{
                            const option = document.createElement('option');
                            option.value = item['Índice'];
                            option.textContent = `[${{item['Tema/Subtema/Tópico']}}] ${{item['Título']}}`;
                            itemSelect.appendChild(option);
                        }});
                    }}
                }});
        
                // Listener para mudança de item
                itemSelect.addEventListener('change', function() {{
                    const indiceSelecionado = this.value;
                    if (indiceSelecionado) {{
                        const itemSelecionado = data.find(row => row['Índice'].toString() === indiceSelecionado);
                        if (itemSelecionado) {{
                            updateChart(itemSelecionado);
                            updateMetrics(itemSelecionado);
                        }}
                    }} else {{
                        document.getElementById('chartContainer').innerHTML = '';
                        document.getElementById('metricsContainer').style.display = 'none';
                    }}
                }});

                // Disparar evento para popular itens inicialmente
                tipoSelect.dispatchEvent(new Event('change'));
            }}

            // Função para atualizar métricas
            function updateMetrics(item) {{
                const metricsContainer = document.getElementById('metricsContainer');
                const totalQuestoes = document.getElementById('totalQuestoes');
                const participacaoTotal = document.getElementById('participacaoTotal');
                const mediaAnual = document.getElementById('mediaAnual');

                const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                const totalAnual = anos.reduce((sum, ano) => sum + (item[ano] || 0), 0);
                const media = totalAnual / anos.length;

                totalQuestoes.textContent = item['Contagem Total'] || 0;
                participacaoTotal.textContent = ((item['Participação Total'] || 0) * 100).toFixed(1) + '%';
                mediaAnual.textContent = media.toFixed(1);

                metricsContainer.style.display = 'flex';
            }}

            // Função para atualizar o gráfico
            function updateChart(item) {{
                const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                
                const questoesPorAno = anos.map(ano => item[ano] || 0);
                
                // ALTERAÇÃO: Calcular participação percentual baseada no tipo do item
                const participacaoAnual = anos.map(ano => {{
                    const questoes = item[ano] || 0;
                    const tipoItem = item['Tema/Subtema/Tópico'];
                    const totalDoTipo = window.totaisPorTipoEAno[ano][tipoItem] || 1;
                    return questoes === 0 ? 0 : (questoes / totalDoTipo * 100);
                }});

                // Criar texto para hover
                const hoverText = anos.map((ano, index) => {{
                    const tipoItem = item['Tema/Subtema/Tópico'];
                    const totalDoTipo = window.totaisPorTipoEAno[ano][tipoItem] || 0;
                    
                    return `<b>${{ano}}</b><br>` +
                        `Questões: ${{questoesPorAno[index]}}<br>` +
                        `Participação: ${{participacaoAnual[index].toFixed(1)}}%<br>` +
                        `Total de ${{tipoItem.toLowerCase()}}s: ${{totalDoTipo}}<br>` +
                        `<b>Dados Gerais:</b><br>` +
                        `Total geral: ${{item['Contagem Total']}}<br>` +
                        `Participação total: ${{((item['Participação Total'] || 0) * 100).toFixed(1)}}%`;
                }});

                const trace = {{
                    x: anos,
                    y: participacaoAnual,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Participação % por Ano',
                    line: {{
                        color: '#2196f3',
                        width: 3
                    }},
                    marker: {{
                        size: 8,
                        color: '#1976d2',
                        line: {{
                            color: '#0d47a1',
                            width: 2
                        }}
                    }},
                    hovertemplate: '%{{text}}<extra></extra>',
                    text: hoverText
                }};

                const layout = {{
                    title: {{
                        text: `<b>${{item['Título']}}</b><br><sub>[${{item['Tema/Subtema/Tópico']}}]</sub>`,
                        font: {{
                            size: 16
                        }}
                    }},
                    xaxis: {{
                        title: 'Ano',
                        showgrid: true,
                        gridcolor: '#e0e0e0'
                    }},
                    yaxis: {{
                        title: 'Participação (%)',
                        showgrid: true,
                        gridcolor: '#e0e0e0'
                    }},
                    plot_bgcolor: '#fafafa',
                    paper_bgcolor: 'white',
                    hovermode: 'x unified',
                    margin: {{
                        l: 60,
                        r: 40,
                        t: 80,
                        b: 60
                    }}
                }};

                const config = {{
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
                    displaylogo: false
                }};

                Plotly.newPlot('chartContainer', [trace], layout, config);
            }}

                    

            // Inicializar aplicação
            window.addEventListener('load', processData);
        </script>
    </body>
    </html>
            """, height=800, scrolling=True)
            
            # Seção de download no final da página
            st.markdown("---")
            st.markdown("### 📥 Download dos Dados")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                try:
                    # Verificar se o arquivo Excel existe
                    if os.path.exists('gráficos.xlsx'):
                        with open('gráficos.xlsx', 'rb') as file:
                            excel_data = file.read()
                        
                        st.download_button(
                            label="📊 Baixar gráficos.xlsx",
                            data=excel_data,
                            file_name="graficos_uerj_quimica.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixar arquivo Excel com todos os dados estatísticos",
                            use_container_width=True
                        )
                    else:
                        # Se não existir arquivo Excel, criar a partir do CSV
                        df_excel = pd.read_csv('gráficos.csv')
                        buffer = BytesIO()
                        df_excel.to_excel(buffer, index=False, engine='openpyxl')
                        excel_data = buffer.getvalue()
                        
                        st.download_button(
                            label="📊 Baixar dados em Excel",
                            data=excel_data,
                            file_name="graficos_uerj_quimica.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixar arquivo Excel gerado a partir dos dados CSV",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"❌ Erro ao preparar download: {str(e)}")
                    st.info("📋 Verifique se o arquivo está disponível ou tente novamente.")
                
        except FileNotFoundError:
            st.error("❌ Arquivo 'gráficos.csv' não encontrado!")
            st.info("📁 Certifique-se de que o arquivo 'gráficos.csv' está na mesma pasta do aplicativo.")
            
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {str(e)}")
            st.info("📋 Verifique o formato do arquivo CSV e tente novamente.")        


    if __name__ == "__main__":
        main()
        
    
#########################################################################################################################
#########################################################################################################################
#########################################################################################################################
#########################################################################################################################
#########################################################################################################################
#########################################################################################################################

if st.session_state.selected_option == "Biologia":

    # Configuração da página
    st.set_page_config(
        page_title="Gerador de Questões Discursivas UERJ - Biologia",
        page_icon="🧬",
        layout="wide"
    )

    # Função para inicializar o cliente Anthropic
    @st.cache_resource
    def init_anthropic_client():
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
            return anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            st.error(f"Erro ao inicializar cliente Anthropic: {e}")
            st.error("Verifique se a chave ANTHROPIC_API_KEY está configurada nos secrets do Streamlit.")
            return None

    @st.cache_data
    def carregar_contexto_arquivo(topico_id):
        """Carrega o contexto de um arquivo .txt específico"""
        # Mapeamento de tópico para nome do arquivo
        mapeamento_arquivos = {
            "1.1.1": "Bio_1.1.1 - Biodiversidade - características gerais dos principais grupos de seres vivos; teorias e conceitos de evolução.txt",
            "1.2.1": "Bio_1.2.1 - Integração entre seres vivos e meio ambiente - ecossistemas, cadeia alimentar, ciclos biogeoquímicos; poluição e desequilíbrio ecológico.txt",
            "1.3.1": "Bio_1.3.1 - A célula - funções das estruturas e organelas; fases da divisão celular.txt",
            "1.4.1": "Bio_1.4.1 - As bases da genética - genes; código genético; cromossomos; hereditariedade e doenças hereditárias.txt",
            "1.5.1": "Bio_1.5.1 - Doenças parasitárias - ciclos de vida de parasitas, modos de transmissão; profilaxia.txt",
            "1.6.1": "Bio_1.6.1 - Sistemas vitais dos animais e vegetais - homeostase, digestão e absorção dos alimentos; respiração; circulação; excreção; metabolismo de carboidratos, de lipídio.txt",
            "1.6.2": "Bio_1.6.2 - Sistemas vitais dos animais e vegetais - sistemas reprodutores; produção de óvulos e espermatozoides na reprodução humana; atuação dos hormônios sexuais.txt",
            "1.6.3": "Bio_1.6.3 - Sistemas vitais dos animais e vegetais - fotossíntese.txt"
        }
        
        nome_arquivo = mapeamento_arquivos.get(topico_id)
        if nome_arquivo:
            try:
                with open(nome_arquivo, 'r', encoding='utf-8') as file:
                    conteudo = file.read()
                    return conteudo
            except FileNotFoundError:
                st.warning(f"⚠️ Arquivo {nome_arquivo} não encontrado. Usando contexto padrão.")
                return None
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo {nome_arquivo}: {str(e)}")
                return None
        return None




    # Estrutura hierárquica dos temas
    ESTRUTURA_TEMAS = {
        "1.": {
            "titulo": "Os seres vivos e sua relação com o ambiente",
            "subtemas": {
                "1.1": {
                    "titulo": "Biodiversidade",
                    "topicos": {
                        "1.1.1": "Biodiversidade - características gerais dos principais grupos de seres vivos; teorias e conceitos de evolução"
                    }
                },
                "1.2": {
                    "titulo": "Integração entre seres vivos e meio ambiente",
                    "topicos": {
                        "1.2.1": "Integração entre seres vivos e meio ambiente - ecossistemas, cadeia alimentar, ciclos biogeoquímicos; poluição e desequilíbrio ecológico"
                    }
                },
                "1.3": {
                    "titulo": "A célula",
                    "topicos": {
                        "1.3.1": "A célula - funções das estruturas e organelas; fases da divisão celular"
                    }
                },
                "1.4": {
                    "titulo": "As bases da genética",
                    "topicos": {
                        "1.4.1": "As bases da genética - genes; código genético; cromossomos; hereditariedade e doenças hereditárias"
                    }
                },
                "1.5": {
                    "titulo": "Doenças parasitárias",
                    "topicos": {
                        "1.5.1": "Doenças parasitárias - ciclos de vida de parasitas, modos de transmissão; profilaxia"
                    }
                },
                "1.6": {
                    "titulo": "Sistemas vitais dos animais e vegetais",
                    "topicos": {
                        "1.6.1": "Sistemas vitais dos animais e vegetais - homeostase, digestão e absorção dos alimentos; respiração; circulação; excreção; metabolismo de carboidratos, de lipídios e de proteínas; funções dos hormônios no metabolismo",
                        "1.6.2": "Sistemas vitais dos animais e vegetais - sistemas reprodutores; produção de óvulos e espermatozoides na reprodução humana; atuação dos hormônios sexuais",
                        "1.6.3": "Sistemas vitais dos animais e vegetais - fotossíntese"
                    }
                }
            }
        }
    }

    # Contextos específicos para os tópicos disponíveis
    CONTEXTOS_TOPICOS = {
        "1.1.1": """
    ## CONTEXTO: Biodiversidade - características gerais dos principais grupos de seres vivos; teorias e conceitos de evolução (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Características gerais dos principais grupos de seres vivos - classificação taxonômica
    - Diversidade biológica e importância ecológica
    - Teorias evolutivas - Darwin, Lamarck, teorias modernas
    - Conceitos de evolução - seleção natural, adaptação, especiação
    - Evidências evolutivas - registro fóssil, anatomia comparada, embriologia
    - Evolução molecular e filogenética
    - Biodiversidade e conservação
    - Endemismo e distribuição geográfica das espécies
    - Fatores que influenciam a biodiversidade
    - Impactos humanos na biodiversidade

    Exemplos de questões discursivas incluem:
    - Classificação taxonômica de grupos específicos
    - Análise de características evolutivas adaptativas
    - Comparação entre diferentes teorias evolutivas
    - Interpretação de árvores filogenéticas
    - Impactos da ação humana na biodiversidade
    - Estratégias de conservação da biodiversidade
    """,
        "1.2.1": """
    ## CONTEXTO: Integração entre seres vivos e meio ambiente - ecossistemas, cadeia alimentar, ciclos biogeoquímicos; poluição e desequilíbrio ecológico (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Estrutura e funcionamento dos ecossistemas - componentes bióticos e abióticos
    - Cadeias e teias alimentares - fluxo de energia e matéria
    - Níveis tróficos e pirâmides ecológicas
    - Ciclos biogeoquímicos - carbono, nitrogênio, fósforo, água
    - Fatores limitantes e capacidade de suporte
    - Sucessão ecológica primária e secundária
    - Poluição ambiental e seus efeitos nos ecossistemas
    - Desequilíbrio ecológico e suas consequências
    - Mudanças climáticas e impactos ambientais
    - Desenvolvimento sustentável e conservação

    Exemplos de questões discursivas incluem:
    - Análise de cadeias alimentares complexas
    - Interpretação de ciclos biogeoquímicos
    - Efeitos da poluição em ecossistemas específicos
    - Sucessão ecológica em diferentes ambientes
    - Impactos das mudanças climáticas
    - Estratégias de manejo ambiental
    """,
        "1.3.1": """
    ## CONTEXTO: A célula - funções das estruturas e organelas; fases da divisão celular (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Estrutura celular - membrana plasmática, citoplasma, núcleo
    - Organelas celulares e suas funções específicas
    - Diferenças entre células procarióticas e eucarióticas
    - Diferenças entre células animais e vegetais
    - Processos de transporte através da membrana
    - Metabolismo celular - respiração, fotossíntese, fermentação
    - Ciclo celular e sua regulação
    - Fases da mitose e sua importância
    - Fases da meiose e variabilidade genética
    - Controle do ciclo celular e câncer

    Exemplos de questões discursivas incluem:
    - Comparação entre diferentes tipos celulares
    - Análise de processos metabólicos celulares
    - Interpretação de experimentos sobre divisão celular
    - Relação entre estrutura e função de organelas
    - Mecanismos de regulação do ciclo celular
    - Importância da divisão celular para os organismos
    """,
        "1.4.1": """
    ## CONTEXTO: As bases da genética - genes; código genético; cromossomos; hereditariedade e doenças hereditárias (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Conceitos básicos de genética - genes, alelos, genótipo, fenótipo
    - Estrutura e organização dos cromossomos
    - Código genético e síntese de proteínas
    - Leis de Mendel e padrões de herança
    - Herança ligada ao sexo e herança quantitativa
    - Mutações gênicas e cromossômicas
    - Doenças genéticas e hereditárias
    - Aconselhamento genético e diagnóstico
    - Biotecnologia e engenharia genética
    - Terapia gênica e medicina personalizada

    Exemplos de questões discursivas incluem:
    - Resolução de problemas de genética mendeliana
    - Análise de heredogramas e padrões de herança
    - Interpretação de experimentos genéticos
    - Relação entre genótipo e fenótipo
    - Mecanismos de origem de doenças genéticas
    - Aplicações da biotecnologia na medicina
    """,
        "1.5.1": """
    ## CONTEXTO: Doenças parasitárias - ciclos de vida de parasitas, modos de transmissão; profilaxia (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Principais grupos de parasitas - protozoários, helmintos, artrópodes
    - Ciclos de vida complexos dos parasitas
    - Modos de transmissão - vetores, hospedeiros intermediários
    - Doenças parasitárias no Brasil - malária, dengue, esquistossomose
    - Sintomas e diagnóstico de doenças parasitárias
    - Medidas profiláticas e controle de vetores
    - Tratamento de doenças parasitárias
    - Epidemiologia e saúde pública
    - Fatores socioeconômicos e doenças parasitárias
    - Impactos ambientais no ciclo dos parasitas

    Exemplos de questões discursivas incluem:
    - Análise de ciclos de vida de parasitas específicos
    - Estratégias de controle e prevenção
    - Interpretação de dados epidemiológicos
    - Relação entre condições ambientais e parasitoses
    - Medidas de saúde pública para controle
    - Diagnóstico diferencial de doenças parasitárias
    """,
        "1.6.1": """
    ## CONTEXTO: Sistemas vitais dos animais e vegetais - homeostase, digestão e absorção dos alimentos; respiração; circulação; excreção; metabolismo de carboidratos, de lipídios e de proteínas; funções dos hormônios no metabolismo (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Homeostase e mecanismos de regulação
    - Sistema digestório - digestão e absorção
    - Sistema respiratório - trocas gasosas
    - Sistema circulatório - transporte de substâncias
    - Sistema excretor - eliminação de resíduos
    - Metabolismo de carboidratos, lipídios e proteínas
    - Regulação hormonal do metabolismo
    - Integração entre sistemas orgânicos
    - Adaptações fisiológicas em diferentes ambientes
    - Distúrbios metabólicos e doenças

    Exemplos de questões discursivas incluem:
    - Análise de processos fisiológicos integrados
    - Mecanismos de controle homeostático
    - Interpretação de experimentos fisiológicos
    - Relação entre estrutura e função em órgãos
    - Regulação hormonal de processos metabólicos
    - Adaptações fisiológicas em diferentes organismos
    """,
        "1.6.2": """
    ## CONTEXTO: Sistemas vitais dos animais e vegetais - sistemas reprodutores; produção de óvulos e espermatozoides na reprodução humana; atuação dos hormônios sexuais (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Sistemas reprodutores masculino e feminino
    - Gametogênese - espermatogênese e ovogênese
    - Ciclo menstrual e regulação hormonal
    - Fecundação e desenvolvimento embrionário
    - Hormônios sexuais e suas funções
    - Métodos contraceptivos e planejamento familiar
    - Reprodução assistida e biotecnologia reprodutiva
    - Doenças sexualmente transmissíveis
    - Puberdade e desenvolvimento sexual
    - Menopausa e andropausa

    Exemplos de questões discursivas incluem:
    - Análise do ciclo menstrual e regulação hormonal
    - Processos de gametogênese e maturação
    - Mecanismos de ação de métodos contraceptivos
    - Técnicas de reprodução assistida
    - Interpretação de dados sobre fertilidade
    - Prevenção de doenças sexualmente transmissíveis
    """,
        "1.6.3": """
    ## CONTEXTO: Sistemas vitais dos animais e vegetais - fotossíntese (QUESTÕES DISCURSIVAS)

    Baseado nas questões discursivas de vestibulares UERJ, este tópico aborda:
    - Processo fotossintético - fase clara e fase escura
    - Estrutura dos cloroplastos e pigmentos fotossintéticos
    - Fatores que influenciam a fotossíntese
    - Fotossíntese e respiração celular - relação e diferenças
    - Importância ecológica da fotossíntese
    - Plantas C3, C4 e CAM - adaptações fotossintéticas
    - Fotossíntese artificial e biotecnologia
    - Mudanças climáticas e fotossíntese
    - Eficiência fotossintética e produtividade
    - Fotossíntese em diferentes ambientes

    Exemplos de questões discursivas incluem:
    - Análise experimental da fotossíntese
    - Fatores limitantes do processo fotossintético
    - Adaptações fotossintéticas em diferentes plantas
    - Relação entre fotossíntese e respiração
    - Importância da fotossíntese nos ecossistemas
    - Aplicações biotecnológicas da fotossíntese
    """
    }

    def get_contexto_completo(topico_id):
        """Retorna o contexto completo para um tópico específico"""
        # Primeiro tenta carregar do arquivo .txt
        contexto_arquivo = carregar_contexto_arquivo(topico_id)
        
        if contexto_arquivo:
            # Se arquivo foi carregado com sucesso, usa seu conteúdo
            return contexto_arquivo
        else:
            # Fallback para contexto hardcoded se arquivo não existir
            contexto_base = CONTEXTOS_TOPICOS.get(topico_id, "")
            
            # Adiciona exemplos de questões baseados nos tópicos de biologia
            if topico_id in ["1.1.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Classificação taxonômica e características evolutivas
    - Teorias evolutivas e evidências científicas
    - Biodiversidade e conservação ambiental
    - Adaptações evolutivas e seleção natural
    - Impactos humanos na biodiversidade
    """
            elif topico_id in ["1.2.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Análise de cadeias alimentares e fluxo de energia
    - Ciclos biogeoquímicos e equilíbrio ambiental
    - Poluição e desequilíbrio ecológico
    - Sucessão ecológica e regeneração ambiental
    - Mudanças climáticas e impactos nos ecossistemas
    """
            elif topico_id in ["1.3.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Estrutura e função de organelas celulares
    - Processos de divisão celular e regulação
    - Diferenças entre tipos celulares
    - Metabolismo celular e energia
    - Ciclo celular e controle da proliferação
    """
            elif topico_id in ["1.4.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Genética mendeliana e padrões de herança
    - Análise de heredogramas e aconselhamento genético
    - Doenças genéticas e mutações
    - Biotecnologia e engenharia genética
    - Código genético e síntese de proteínas
    """
            elif topico_id in ["1.5.1"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Ciclos de vida de parasitas e vetores
    - Doenças parasitárias e epidemiologia
    - Medidas profiláticas e controle de vetores
    - Diagnóstico e tratamento de parasitoses
    - Saúde pública e doenças tropicais
    """
            elif topico_id in ["1.6.1", "1.6.2", "1.6.3"]:
                contexto_base += """

    ### EXEMPLOS DE QUESTÕES DETALHADAS:
    - Fisiologia dos sistemas orgânicos
    - Homeostase e regulação hormonal
    - Processos reprodutivos e desenvolvimento
    - Fotossíntese e metabolismo energético
    - Integração entre sistemas biológicos
    """
            
            return contexto_base

    def gerar_questao(client, tema, subtema, topico, num_questoes, dificuldade):
        """Gera questões discursivas usando a API do Claude"""
        
        contexto_topico = get_contexto_completo(topico.split(' ', 1)[0] if ' ' in topico else topico)
        
        prompt = f"""
    Como professor experiente de Biologia da UERJ, elabore EXATAMENTE {num_questoes} questão(ões) discursiva(s) original(is) sobre o tópico:

    **TEMA:** {tema}
    **SUBTEMA:** {subtema}  
    **TÓPICO:** {topico}

    **CONTEXTO DO TÓPICO:**
    {contexto_topico}

    **INSTRUÇÕES ESPECÍFICAS:**
    1. Crie APENAS questões DISCURSIVAS no estilo UERJ (contextualizada, interdisciplinar quando possível)
    2. Dificuldade: {dificuldade}
    3. Inclua dados necessários, tabelas ou gráficos quando apropriado
    4. As questões devem ser claras, bem estruturadas e desafiadoras
    5. NÃO use alternativas de múltipla escolha - apenas questões abertas
    6. Use contextos reais e aplicações práticas
    7. Inclua cálculos quando necessário
    8. Mantenha consistência com o padrão UERJ de questões discursivas

    **CARACTERÍSTICAS DAS QUESTÕES DISCURSIVAS UERJ:**
    - Contextualização com situações reais e atuais
    - Interdisciplinaridade quando possível
    - Múltiplas habilidades em uma questão
    - Dados experimentais ou situações práticas
    - Aplicação de conceitos teóricos em contextos reais
    - Respostas que exigem desenvolvimento, explicação e justificativa
    - Questões que avaliam capacidade de análise e síntese

    **FORMATO OBRIGATÓRIO DE RESPOSTA:**
    Para cada questão, forneça EXATAMENTE:

    """ + "\n".join([f"""
    ### QUESTÃO {i}
    [Enunciado completo com contexto rico e situação real]

    [Dados, tabelas ou informações complementares se necessário]

    **O que se pede:**
    a) [Primeira pergunta discursiva]
    b) [Segunda pergunta discursiva]
    c) [Terceira pergunta discursiva - se aplicável]""" for i in range(1, num_questoes + 1)]) + f"""

    """ + "\n".join([f"""
    ### GABARITO E SOLUÇÃO DETALHADA {i}
    **Solução completa:**

    **Item a)**
    [Resposta esperada detalhada]
    [Desenvolvimento passo a passo]
    [Cálculos quando necessário]

    **Item b)**
    [Resposta esperada detalhada]
    [Desenvolvimento passo a passo]
    [Justificativas teóricas]

    **Item c)** (se aplicável)
    [Resposta esperada detalhada]
    [Explicações conceituais]

    **Conceitos envolvidos:**
    - [conceito biológico 1]
    - [conceito biológico 2]
    - [conceito biológico 3]
    - [aplicações práticas]""" for i in range(1, num_questoes + 1)]) + f"""

    ---

    IMPORTANTE: Gere EXATAMENTE {num_questoes} questão(ões) discursiva(s) agora, seguindo rigorosamente este formato. NÃO inclua alternativas de múltipla escolha."""

        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
                    
            return response.content[0].text
        except Exception as e:
            st.error(f"Erro detalhado: {str(e)}")
            return f"❌ **Erro ao gerar questão**\n\nDetalhes técnicos: {str(e)}"

    def main():
        st.title("🧬 Gerador de Questões Discursivas UERJ - Biologia")
        st.markdown("*Sistema inteligente para criação de questões discursivas de vestibular baseado no padrão UERJ*")

        # Sistema de navegação
        tab1, tab2 = st.tabs(["🚀 Gerador de Questões", "📊 Análise Estatística"])
        
        with tab1:
            # Inicializar cliente
            client = init_anthropic_client()
            if not client:
                st.stop()
            
            # CSS personalizado para melhorar aparência
            st.markdown("""
            <style>
            .stSelectbox > div > div > select {
                background-color: #f0f2f6;
            }
            .success-box {
                padding: 1rem;
                border-radius: 0.5rem;
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                margin: 1rem 0;
            }
            .info-card {
                padding: 1.5rem;
                border-radius: 0.5rem;
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                margin: 1rem 0;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Sidebar para seleção
            st.sidebar.header("⚙️ Configurações")
            
            # Seleção do tema
            temas_opcoes = {f"{k} {v['titulo']}": k for k, v in ESTRUTURA_TEMAS.items()}
            tema_selecionado = st.sidebar.selectbox(
                "📚 Selecione o Tema:",
                list(temas_opcoes.keys()),
                help="Escolha o tema principal do conteúdo"
            )
            tema_id = temas_opcoes[tema_selecionado]
            
            # Seleção do subtema
            subtemas_disponiveis = ESTRUTURA_TEMAS[tema_id]["subtemas"]
            subtemas_opcoes = {f"{k} {v['titulo']}": k for k, v in subtemas_disponiveis.items()}
            subtema_selecionado = st.sidebar.selectbox(
                "📖 Selecione o Subtema:",
                list(subtemas_opcoes.keys()),
                help="Escolha o subtema específico"
            )
            subtema_id = subtemas_opcoes[subtema_selecionado]
            
            # Seleção do tópico
            topicos_disponiveis = subtemas_disponiveis[subtema_id]["topicos"]
            if topicos_disponiveis:
                topicos_opcoes = {f"{k} {v}": k for k, v in topicos_disponiveis.items()}
                topico_selecionado = st.sidebar.selectbox(
                    "📝 Selecione o Tópico:",
                    list(topicos_opcoes.keys()),
                    help="Escolha o tópico específico para a questão"
                )
                topico_id = topicos_opcoes[topico_selecionado]
                contexto_disponivel = topico_id in CONTEXTOS_TOPICOS
            else:
                st.sidebar.warning("⚠️ Este subtema não possui tópicos específicos disponíveis.")
                topico_selecionado = subtema_selecionado
                topico_id = subtema_id
                contexto_disponivel = False
            
            # Indicador de contexto disponível
            if contexto_disponivel:
                # Verificar se o contexto vem de arquivo ou é hardcoded
                contexto_arquivo = carregar_contexto_arquivo(topico_id)
                if contexto_arquivo:
                    st.sidebar.success("✅ Contexto especializado carregado do arquivo")
                else:
                    st.sidebar.success("✅ Contexto especializado disponível")
            else:
                st.sidebar.info("ℹ️ Usando contexto geral do subtema")
                    
            # Configurações adicionais
            st.sidebar.markdown("### 🎛️ Parâmetros de Geração")
            
            # Seleção do número de questões
            num_questoes = st.sidebar.slider("🔢 Número de questões:", 1, 5, 1)
            dificuldade = st.sidebar.selectbox(
                "📊 Nível de dificuldade:",
                ["fácil", "média", "difícil"]
            )
                
            # Configurações avançadas
            with st.sidebar.expander("🔧 Características das Questões"):
                st.markdown("""
                ✅ **Formato:** Apenas questões discursivas  
                ✅ **Estrutura:** Contexto + múltiplos itens  
                ✅ **Estilo:** Padrão UERJ contextualizado  
                ✅ **Quantidade:** Entre 1 e 5: o usuário escolhe  
                ✅ **Cálculos:** Incluídos quando necessário  
                ✅ **Interdisciplinar:** Quando aplicável  
                """)
            
            # Botão para gerar questões
            texto_botao = f"🚀 Gerar {num_questoes} Questão{'s' if num_questoes > 1 else ''} Discursiva{'s' if num_questoes > 1 else ''}"
            gerar_button = st.sidebar.button(texto_botao, type="primary", use_container_width=True)
                
            if gerar_button:
                # Validações
                if not client:
                    st.error("❌ Cliente Anthropic não inicializado. Verifique a configuração da API key.")
                    return
                    
                # Mostrar informações da seleção
                st.markdown("### 📋 Questões Sendo Geradas:")
                
                # Verificar fonte do contexto
                contexto_arquivo = carregar_contexto_arquivo(topico_id) if contexto_disponivel else None
                fonte_contexto = "Arquivo especializado" if contexto_arquivo else ("Especializado" if contexto_disponivel else "Geral")
                
                st.markdown(f"""
                <div class="info-card">
                <strong>📚 Tema:</strong> {tema_selecionado}<br>
                <strong>📖 Subtema:</strong> {subtema_selecionado}<br>
                <strong>📝 Tópico:</strong> {topico_selecionado}<br>
                <strong>📊 Dificuldade:</strong> {dificuldade.title()}<br>
                <strong>🎯 Contexto:</strong> {fonte_contexto}<br>
                <strong>📁 Fonte:</strong> {'Arquivo .txt' if contexto_arquivo else 'Código interno'}<br>
                <strong>🔢 Quantidade:</strong> {num_questoes} questão{'ões' if num_questoes > 1 else ''} discursiva{'s' if num_questoes > 1 else ''}<br>
                </div>
                """, unsafe_allow_html=True)
                        
                # Progresso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("🔄 Gerando questões... Por favor, aguarde."):
                    status_text.text("🤖 Conectando com IA...")
                    progress_bar.progress(25)
                    
                    status_text.text(f"📝 Elaborando {num_questoes} questão{'ões' if num_questoes > 1 else ''} discursiva{'s' if num_questoes > 1 else ''}...")

                    progress_bar.progress(50)
                    
                    resultado = gerar_questao(
                        client, 
                        tema_selecionado, 
                        subtema_selecionado, 
                        topico_selecionado,
                        num_questoes,
                        dificuldade
                    )
                    
                    status_text.text("✅ Processando resultado...")
                    progress_bar.progress(75)
                    
                    progress_bar.progress(100)
                    status_text.text(f"🎉 {num_questoes} questão{'ões' if num_questoes > 1 else ''} gerada{'s' if num_questoes > 1 else ''} com sucesso!")

                
                # Limpar elementos de progresso após um delay
                import time
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
                # Verificar se houve erro
                if resultado.startswith("❌"):
                    st.error(resultado)
                    return
                
                # Exibir resultado
                st.markdown("---")
                st.markdown("## 📋 Questões Geradas")
                
                # Dividir o resultado em questões e gabaritos
                partes = resultado.split("### GABARITO E SOLUÇÃO DETALHADA")
                
                if len(partes) > 1:
                    # Exibir questões
                    questoes_parte = partes[0]
                    st.markdown(questoes_parte)
                    
                    # Botão para download das questões (futuro)
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        st.markdown("""
                        <div class="success-box">
                        ✅ Questões geradas com sucesso! Use os expanders abaixo para ver as soluções.
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Exibir gabaritos em expanders
                    st.markdown("---")
                    st.markdown("## 🔑 Gabaritos e Soluções Detalhadas")
                    st.markdown("*Clique nos cards abaixo para visualizar as soluções completas*")
                    
                    for i in range(1, len(partes)):
                        gabarito_parte = "### GABARITO E SOLUÇÃO DETALHADA" + partes[i]
                        
                        # Extrair número da questão para o título do expander
                        linhas = gabarito_parte.split('\n')
                        titulo_questao = linhas[0].replace("### GABARITO E SOLUÇÃO DETALHADA", "Solução da Questão") if linhas else f"Solução da Questão {i}"
                        
                        with st.expander(f"💡 {titulo_questao}", expanded=False):
                            st.markdown(gabarito_parte)
                            
                            # Botões de ação para cada solução
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button(f"📋 Copiar Questão {i}", key=f"copy_{i}"):
                                    st.success("Funcionalidade de cópia será implementada!")
                            with col2:
                                if st.button(f"⭐ Favoritar {i}", key=f"fav_{i}"):
                                    st.success("Questão favoritada!")
                else:
                    # Se não conseguiu dividir, exibir tudo
                    st.markdown(resultado)
                    
                # Feedback do usuário
                st.markdown("---")
                st.markdown("### 📝 Feedback")
                col1, col2 = st.columns([1, 1])
                with col1:
                    rating = st.selectbox("Avalie a qualidade das questões:", 
                                        ["Selecione...", "⭐ Ruim", "⭐⭐ Regular", "⭐⭐⭐ Bom", "⭐⭐⭐⭐ Muito Bom", "⭐⭐⭐⭐⭐ Excelente"])
                with col2:
                    if st.button("📤 Enviar Feedback"):
                        if rating != "Selecione...":
                            st.success("Obrigado pelo feedback!")
                        else:
                            st.warning("Por favor, selecione uma avaliação.")
            
            # Informações adicionais na sidebar
            st.sidebar.markdown("---")
            st.sidebar.markdown("### ℹ️ Informações do Sistema")
            st.sidebar.info(
                "🤖 **IA:** Claude Sonnet 4\n\n"
                "📊 **Base:** Questões UERJ reais\n\n"
                "📝 **Formato:** Apenas discursivas\n\n"
                "🔢 **Quantidade:** 1-5 questões/geração\n\n"
                "✅ **Status:** Operacional"
            )
            
            # Estatísticas na sidebar
            with st.sidebar.expander("📈 Estatísticas"):
                st.markdown("""
                **Temas disponíveis:** 1  
                **Subtemas:** 6  
                **Tópicos específicos:** 8  
                **Contextos detalhados:** 8  
                **Formato:** Questões discursivas apenas
                **Questões por geração:** 1-5 (configurável)
                
                **Última atualização:** Dezembro 2024
                """)
                    
            # Área principal com informações quando nenhuma questão foi gerada
            if not gerar_button:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("""
                    ### 🎯 Como usar este sistema:
                    
                    1. **📚 Selecione o tema** na barra lateral
                    2. **📖 Escolha o subtema** relacionado
                    3. **📝 Escolha o tópico específico** (quando disponível)
                    4. **⚙️ Configure** o número de questões e dificuldade
                    5. **🚀 Clique em "Gerar Questões"** para criar as questões
                    
                    ### 🔬 Todos os Tópicos com contexto especializado:
                    - ✅ **Tema 1:** 8 tópicos com contexto completo
                    - 📁 **Fonte:** Arquivos .txt com questões dos vestibulares de 2013 a 2025
                    
                    ### 📊 Recursos do sistema:
                    - ✅ Questões contextualizadas no estilo UERJ
                    - ✅ Gabaritos com soluções detalhadas passo a passo
                    - ✅ Múltiplos níveis de dificuldade
                    - ✅ Baseado em questões reais de vestibulares
                    - ✅ Interface intuitiva e responsiva
                    - ✅ Sistema de feedback integrado
                    """)
                
                with col2:
                    st.markdown("""
                    ### 📈 Visão Geral dos Conteúdos:
                    
                    **🧬 Tema 1 - Os seres vivos e sua relação com o ambiente:**
                    - 6 subtemas principais
                    - 8 tópicos específicos
                    - Foco em biodiversidade, ecologia, célula, genética, parasitoses e fisiologia
                                
                    ### 🔧 Tecnologia:
                    - 🤖 Claude Sonnet 4 (Anthropic)
                    - 🐍 Python + Streamlit
                    - 📊 Interface responsiva
                    - 🔒 API keys protegidas
                    """)
            
            # Informações adicionais
            st.sidebar.markdown("---")
            st.sidebar.markdown("### ℹ️ Informações")
            st.sidebar.info(
                "Este gerador utiliza inteligência artificial para criar questões "
                "baseadas no padrão e contexto das provas da UERJ. "
                "As questões são geradas com base nos tópicos selecionados."
            )
        
        with tab2:
            exibir_graficos()
            return  # Importante: return aqui para não executar o resto da função

    def exibir_graficos():
        """Exibe página com gráficos interativos de análise das questões UERJ"""
        st.title("📊 Análise Estatística - Questões de Biologia UERJ")
        st.markdown("*Visualização interativa da evolução dos temas ao longo dos anos (2013-2025)*")
        
        # Carregar dados CSV no Python
        try:
            df = pd.read_csv('bio_graficos.csv')
            st.success("✅ Arquivo de dados carregado com sucesso!")
            
            # Converter dados para JSON para passar ao JavaScript
            dados_json = df.to_json(orient='records')
            
            # Embed do gráfico HTML com dados embutidos
            components.html(f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Análise de Questões de Biologia UERJ</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.26.0/plotly.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .title {{
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }}
            .controls {{
                margin-bottom: 20px;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }}
            .control-group {{
                margin-bottom: 15px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #495057;
            }}
            select {{
                width: 100%;
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }}
            .chart-container {{
                width: 100%;
                height: 600px;
                margin-top: 20px;
            }}
            .info-box {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
            }}
            .filter-options {{
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }}
            .filter-options > div {{
                flex: 1;
                min-width: 200px;
            }}
            .metrics {{
                display: flex;
                gap: 20px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            .metric-card {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #dee2e6;
                flex: 1;
                min-width: 150px;
                text-align: center;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-label {{
                font-size: 12px;
                color: #6c757d;
                margin-top: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="title">Análise de Questões de Biologia - UERJ (2013-2025)</h1>
            
            <div class="info-box">
                <strong>Como usar:</strong> Selecione um tema, subtema ou tópico específico para visualizar sua evolução ao longo dos anos. 
                Passe o mouse sobre os pontos do gráfico para ver informações detalhadas.
            </div>

            <div class="controls">
                <div class="filter-options">
                    <div class="control-group">
                        <label for="tipoSelect">Tipo:</label>
                        <select id="tipoSelect">
                            <option value="">Todos</option>
                            <option value="Tema">Tema</option>
                            <option value="Subtema">Subtema</option>
                            <option value="Tópico">Tópico</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label for="itemSelect">Item:</label>
                        <select id="itemSelect">
                            <option value="">Selecione um item</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="metrics" id="metricsContainer" style="display: none;">
                <div class="metric-card">
                    <div class="metric-value" id="totalQuestoes">0</div>
                    <div class="metric-label">Total de Questões</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="participacaoTotal">0%</div>
                    <div class="metric-label">Participação Total</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="mediaAnual">0</div>
                    <div class="metric-label">Média Anual</div>
                </div>
            </div>

            <div class="chart-container" id="chartContainer"></div>
        </div>

        <script>
            // Dados carregados do Python
            const data = {dados_json};
            let totalQuestoesPorAno = {{}};

            // Função para processar dados
            function processData() {{
                try {{
                    // Calcular total de questões por ano
                    const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                    anos.forEach(ano => {{
                        totalQuestoesPorAno[ano] = data.reduce((sum, row) => sum + (row[ano] || 0), 0);
                    }});

                    // ADIÇÃO: Calcular totais por tipo e ano para participação percentual correta
                    window.totaisPorTipoEAno = {{}};
                    anos.forEach(ano => {{
                        window.totaisPorTipoEAno[ano] = {{
                            'Tema': data.filter(row => row['Tema/Subtema/Tópico'] === 'Tema')
                                    .reduce((sum, row) => sum + (row[ano] || 0), 0),
                            'Subtema': data.filter(row => row['Tema/Subtema/Tópico'] === 'Subtema')
                                        .reduce((sum, row) => sum + (row[ano] || 0), 0),
                            'Tópico': data.filter(row => row['Tema/Subtema/Tópico'] === 'Tópico')
                                        .reduce((sum, row) => sum + (row[ano] || 0), 0)
                        }};
                    }});

                    populateFilters();
                    
                }} catch (error) {{
                    console.error('Erro ao processar dados:', error);
                    document.getElementById('chartContainer').innerHTML = '<p style="text-align: center; color: red;">Erro ao processar os dados.</p>';
                }}
            }}

            // Função para popular os filtros
            function populateFilters() {{
                const tipoSelect = document.getElementById('tipoSelect');
                const itemSelect = document.getElementById('itemSelect');

                // Debug: verificar estrutura dos dados
                console.log('Dados carregados:', data);
                console.log('Primeira linha:', data[0]);

                // Limpar opções anteriores
                itemSelect.innerHTML = '<option value="">Selecione um item</option>';

                // Listener para mudança de tipo
                tipoSelect.addEventListener('change', function() {{
                    const tipoSelecionado = this.value;
                    console.log('Tipo selecionado:', tipoSelecionado);
                    
                    itemSelect.innerHTML = '<option value="">Selecione um item</option>';

                    if (tipoSelecionado) {{
                        const itensFiltrados = data.filter(row => row['Tema/Subtema/Tópico'] === tipoSelecionado);
                        console.log('Itens filtrados:', itensFiltrados);
                        
                        itensFiltrados.forEach(item => {{
                            const option = document.createElement('option');
                            option.value = item['Índice'];
                            option.textContent = item['Título'];
                            itemSelect.appendChild(option);
                        }});
                    }} else {{
                        // Mostrar todos os itens
                        data.forEach(item => {{
                            const option = document.createElement('option');
                            option.value = item['Índice'];
                            option.textContent = `[${{item['Tema/Subtema/Tópico']}}] ${{item['Título']}}`;
                            itemSelect.appendChild(option);
                        }});
                    }}
                }});
        
                // Listener para mudança de item
                itemSelect.addEventListener('change', function() {{
                    const indiceSelecionado = this.value;
                    if (indiceSelecionado) {{
                        const itemSelecionado = data.find(row => row['Índice'].toString() === indiceSelecionado);
                        if (itemSelecionado) {{
                            updateChart(itemSelecionado);
                            updateMetrics(itemSelecionado);
                        }}
                    }} else {{
                        document.getElementById('chartContainer').innerHTML = '';
                        document.getElementById('metricsContainer').style.display = 'none';
                    }}
                }});

                // Disparar evento para popular itens inicialmente
                tipoSelect.dispatchEvent(new Event('change'));
            }}

            // Função para atualizar métricas
            function updateMetrics(item) {{
                const metricsContainer = document.getElementById('metricsContainer');
                const totalQuestoes = document.getElementById('totalQuestoes');
                const participacaoTotal = document.getElementById('participacaoTotal');
                const mediaAnual = document.getElementById('mediaAnual');

                const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                const totalAnual = anos.reduce((sum, ano) => sum + (item[ano] || 0), 0);
                const media = totalAnual / anos.length;

                totalQuestoes.textContent = item['Contagem Total'] || 0;
                participacaoTotal.textContent = ((item['Participação Total'] || 0) * 100).toFixed(1) + '%';
                mediaAnual.textContent = media.toFixed(1);

                metricsContainer.style.display = 'flex';
            }}

            // Função para atualizar o gráfico
            function updateChart(item) {{
                const anos = ['2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2024', '2025'];
                
                const questoesPorAno = anos.map(ano => item[ano] || 0);
                
                // ALTERAÇÃO: Calcular participação percentual baseada no tipo do item
                const participacaoAnual = anos.map(ano => {{
                    const questoes = item[ano] || 0;
                    const tipoItem = item['Tema/Subtema/Tópico'];
                    const totalDoTipo = window.totaisPorTipoEAno[ano][tipoItem] || 1;
                    return questoes === 0 ? 0 : (questoes / totalDoTipo * 100);
                }});

                // Criar texto para hover
                const hoverText = anos.map((ano, index) => {{
                    const tipoItem = item['Tema/Subtema/Tópico'];
                    const totalDoTipo = window.totaisPorTipoEAno[ano][tipoItem] || 0;
                    
                    return `<b>${{ano}}</b><br>` +
                        `Questões: ${{questoesPorAno[index]}}<br>` +
                        `Participação: ${{participacaoAnual[index].toFixed(1)}}%<br>` +
                        `Total de ${{tipoItem.toLowerCase()}}s: ${{totalDoTipo}}<br>` +
                        `<b>Dados Gerais:</b><br>` +
                        `Total geral: ${{item['Contagem Total']}}<br>` +
                        `Participação total: ${{((item['Participação Total'] || 0) * 100).toFixed(1)}}%`;
                }});

                const trace = {{
                    x: anos,
                    y: participacaoAnual,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Participação % por Ano',
                    line: {{
                        color: '#2196f3',
                        width: 3
                    }},
                    marker: {{
                        size: 8,
                        color: '#1976d2',
                        line: {{
                            color: '#0d47a1',
                            width: 2
                        }}
                    }},
                    hovertemplate: '%{{text}}<extra></extra>',
                    text: hoverText
                }};

                const layout = {{
                    title: {{
                        text: `<b>${{item['Título']}}</b><br><sub>[${{item['Tema/Subtema/Tópico']}}]</sub>`,
                        font: {{
                            size: 16
                        }}
                    }},
                    xaxis: {{
                        title: 'Ano',
                        showgrid: true,
                        gridcolor: '#e0e0e0'
                    }},
                    yaxis: {{
                        title: 'Participação (%)',
                        showgrid: true,
                        gridcolor: '#e0e0e0'
                    }},
                    plot_bgcolor: '#fafafa',
                    paper_bgcolor: 'white',
                    hovermode: 'x unified',
                    margin: {{
                        l: 60,
                        r: 40,
                        t: 80,
                        b: 60
                    }}
                }};

                const config = {{
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
                    displaylogo: false
                }};

                Plotly.newPlot('chartContainer', [trace], layout, config);
            }}

            // Inicializar aplicação
            window.addEventListener('load', processData);
        </script>
    </body>
    </html>
            """, height=800, scrolling=True)
            
            # Seção de download no final da página
            st.markdown("---")
            st.markdown("### 📥 Download dos Dados")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                try:
                    # Verificar se o arquivo Excel existe
                    if os.path.exists('bio_graficos.xlsx'):
                        with open('bio_graficos.xlsx', 'rb') as file:
                            excel_data = file.read()
                        
                        st.download_button(
                            label="📊 Baixar bio_graficos.xlsx",
                            data=excel_data,
                            file_name="bio_graficos_uerj_biologia.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixar arquivo Excel com todos os dados estatísticos",
                            use_container_width=True
                        )
                    else:
                        # Se não existir arquivo Excel, criar a partir do CSV
                        df_excel = pd.read_csv('bio_graficos.csv')
                        buffer = BytesIO()
                        df_excel.to_excel(buffer, index=False, engine='openpyxl')
                        excel_data = buffer.getvalue()
                        
                        st.download_button(
                            label="📊 Baixar dados em Excel",
                            data=excel_data,
                            file_name="bio_graficos_uerj_biologia.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Baixar arquivo Excel gerado a partir dos dados CSV",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"❌ Erro ao preparar download: {str(e)}")
                    st.info("📋 Verifique se o arquivo está disponível ou tente novamente.")
                
        except FileNotFoundError:
            st.error("❌ Arquivo 'bio_graficos.csv' não encontrado!")
            st.info("📁 Certifique-se de que o arquivo 'bio_graficos.csv' está na mesma pasta do aplicativo.")
            
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {str(e)}")
            st.info("📋 Verifique o formato do arquivo CSV e tente novamente.")        

    if __name__ == "__main__":
        main()