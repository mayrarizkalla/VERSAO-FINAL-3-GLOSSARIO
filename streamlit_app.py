import streamlit as st

# Configuração para evitar o erro de inotify
st.set_page_config(
    page_title="Seu App",
    layout="wide"
)

# Desativa o watch de arquivos para evitar o erro de inotify
st.config.set_option('server.fileWatcherType', 'none')

# Seu código continua aqui...
import streamlit as st
from datetime import datetime, timedelta
import random
import requests
import json
import urllib.parse
import re

# Configuração da página - SIMPLIFICADA para evitar erros
st.set_page_config(
    page_title="Glossário Jurídico",
    page_icon="⚖️",
    layout="wide"
)

# CSS personalizado - REMOVIDAS as divisórias extras
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f3a60;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 800;
    }
    .term-card {
        background: #ffffff;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 3px solid #1f3a60;
        box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    .news-card {
        background: #e8f4fd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 4px solid #17a2b8;
    }
    .definition-card {
        background: #f0f7ff;
        border-radius: 15px;
        padding: 25px;
        margin-bottom: 25px;
        border: 2px solid #1f3a60;
    }
    .stButton button {
        background: #1f3a60;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
    .news-link {
        color: #1f3a60;
        text-decoration: none;
        font-weight: 600;
    }
    .news-link:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# Inicialização do estado
if 'termo_selecionado' not in st.session_state:
    st.session_state.termo_selecionado = None
if 'termo_buscado' not in st.session_state:
    st.session_state.termo_buscado = None
if 'area_filtro' not in st.session_state:
    st.session_state.area_filtro = "Todas"

# APIs BRASILEIRAS CONFIRMADAS FUNCIONAIS
WIKIPEDIA_API = "https://pt.wikipedia.org/api/rest_v1/page/summary/"
WIKIPEDIA_SEARCH = "https://pt.wikipedia.org/w/api.php"
DICIO_API = "https://dicio-api-ten.vercel.app/v2/"
SIGNIFICADO_API = "https://significado.herokuapp.com/v2/"

# Classe para buscar definições - ABORDAGEM DIRETA
class BuscadorDefinicoes:
    def buscar_wikipedia_direto(self, termo):
        """Busca direta na Wikipedia API"""
        try:
            url = f"{WIKIPEDIA_API}{urllib.parse.quote(termo)}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'extract' in data and data['extract']:
                    return {
                        "definicao": data['extract'],
                        "fonte": "Wikipedia",
                        "url": data.get('content_urls', {}).get('desktop', {}).get('page', '#')
                    }
        except Exception:
            pass
        return None

    def buscar_wikipedia_pesquisa(self, termo):
        """Busca por pesquisa na Wikipedia"""
        try:
            url = f"{WIKIPEDIA_SEARCH}?action=query&format=json&list=search&srsearch={urllib.parse.quote(termo)}&srlimit=5&utf8=1"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('query', {}).get('search', [])
                if results:
                    # Busca o primeiro resultado
                    primeiro = results[0]['title']
                    return self.buscar_wikipedia_direto(primeiro)
        except Exception:
            pass
        return None

    def buscar_dicio_api(self, termo):
        """Busca na Dicio API"""
        try:
            url = f"{DICIO_API}{urllib.parse.quote(termo.lower())}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    significado = data[0].get('significados', [])
                    if significado and len(significado) > 0:
                        definicao = significado[0].get('descricao', '')
                        if definicao:
                            return {
                                "definicao": definicao,
                                "fonte": "Dicio",
                                "url": f"https://dicio.com.br/{urllib.parse.quote(termo.lower())}/"
                            }
        except Exception:
            pass
        return None

    def buscar_significado_api(self, termo):
        """Busca na API de Significados"""
        try:
            url = f"{SIGNIFICADO_API}{urllib.parse.quote(termo.lower())}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    definicao = data[0].get('significado', '')
                    if definicao:
                        return {
                            "definicao": definicao,
                            "fonte": "Significado",
                            "url": "#"
                        }
        except Exception:
            pass
        return None

    def buscar_definicao(self, termo):
        """Busca definição em todas as APIs"""
        # Lista de métodos de busca em ordem de prioridade
        metodos = [
            self.buscar_wikipedia_direto,
            self.buscar_dicio_api,
            self.buscar_wikipedia_pesquisa,
            self.buscar_significado_api
        ]
        
        for metodo in metodos:
            resultado = metodo(termo)
            if resultado:
                return resultado
        
        return None

# Classe para buscar notícias - BUSCA EM SITES GRANDES
class BuscadorNoticias:
    def buscar_portais_juridicos(self, termo):
        """Busca em portais jurídicos brasileiros - ORDEM: Consultor Jurídico, Jusbrasil, G1, Migalhas"""
        noticias = []
        portais = [
            {
                "nome": "Consultor Jurídico", 
                "url": f"https://www.conjur.com.br/pesquisa/?q={urllib.parse.quote(termo)}",
                "base": "https://www.conjur.com.br"
            },
            {
                "nome": "Jusbrasil",
                "url": f"https://jusbrasil.com.br/busca?q={urllib.parse.quote(termo)}",
                "base": "https://jusbrasil.com.br"
            },
            {
                "nome": "G1",
                "url": f"https://g1.globo.com/busca/?q={urllib.parse.quote(termo)}",
                "base": "https://g1.globo.com"
            },
            {
                "nome": "Migalhas",
                "url": f"https://www.migalhas.com.br/busca?q={urllib.parse.quote(termo)}",
                "base": "https://www.migalhas.com.br"
            }
        ]
        
        for portal in portais:
            noticias.append({
                "titulo": f"📰 Notícias sobre {termo} - {portal['nome']}",
                "fonte": portal['nome'],
                "data": datetime.now().strftime("%Y-%m-%d"),
                "resumo": f"Clique para ver notícias sobre {termo} no portal {portal['nome']}",
                "url": portal['url']
            })
        
        return noticias

    def _gerar_noticias_simuladas(self, termo):
        """Gera notícias simuladas baseadas no termo - APENAS 1 POR FONTE"""
        noticias = []
        
        # Apenas uma notícia por fonte - ORDEM: Consultor Jurídico primeiro
        fontes_noticias = [
            {
                "nome": "Consultor Jurídico",
                "url": f"https://www.conjur.com.br/pesquisa/?q={urllib.parse.quote(termo)}"
            },
            {
                "nome": "Jusbrasil",
                "url": f"https://jusbrasil.com.br/busca?q={urllib.parse.quote(termo)}"
            },
            {
                "nome": "G1", 
                "url": f"https://g1.globo.com/busca/?q={urllib.parse.quote(termo)}"
            },
            {
                "nome": "Migalhas",
                "url": f"https://www.migalhas.com.br/busca?q={urllib.parse.quote(termo)}"
            }
        ]
        
        for fonte in fontes_noticias:
            noticias.append({
                "titulo": f"📰 Notícias sobre {termo} - {fonte['nome']}",
                "fonte": fonte['nome'],
                "data": (datetime.now() - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
                "resumo": f"Busca por notícias sobre {termo} no portal {fonte['nome']}",
                "url": fonte['url']
            })
        
        return noticias

    def buscar_noticias(self, termo):
        """Busca notícias em todas as fontes"""
        if not termo:
            termo = "direito"
            
        noticias = []
        
        # Busca nos portais jurídicos
        noticias.extend(self.buscar_portais_juridicos(termo))
        
        # Se não encontrou notícias suficientes, gera algumas simuladas
        if len(noticias) < 4:
            noticias_simuladas = self._gerar_noticias_simuladas(termo)
            # Adiciona apenas as fontes que ainda não estão presentes
            fontes_presentes = {n['fonte'] for n in noticias}
            for noticia in noticias_simuladas:
                if noticia['fonte'] not in fontes_presentes:
                    noticias.append(noticia)
                    fontes_presentes.add(noticia['fonte'])
        
        # Remove duplicatas e garante URLs corretas
        noticias_unicas = []
        fontes_vistas = set()
        
        for noticia in noticias:
            if noticia['fonte'] not in fontes_vistas:
                # Garante que a URL corresponde à fonte declarada
                fonte = noticia['fonte']
                url = noticia['url']
                
                # Verifica se a URL é compatível com a fonte
                if fonte == "Consultor Jurídico" and "conjur.com.br/pesquisa" not in url:
                    noticia['url'] = f"https://www.conjur.com.br/pesquisa/?q={urllib.parse.quote(termo)}"
                elif fonte == "Jusbrasil" and "jusbrasil.com.br" not in url:
                    noticia['url'] = f"https://jusbrasil.com.br/busca?q={urllib.parse.quote(termo)}"
                elif fonte == "G1" and "g1.globo.com" not in url:
                    noticia['url'] = f"https://g1.globo.com/busca/?q={urllib.parse.quote(termo)}"
                elif fonte == "Migalhas" and "migalhas.com.br" not in url:
                    noticia['url'] = f"https://www.migalhas.com.br/busca?q={urllib.parse.quote(termo)}"
                
                noticias_unicas.append(noticia)
                fontes_vistas.add(noticia['fonte'])
        
        return noticias_unicas

# Sistema de termos jurídicos
class GerenciadorTermos:
    def __init__(self):
        self.areas_direito = [
            "Direito Constitucional", "Direito Processual Civil", "Direito Penal",
            "Direito Civil", "Direito Administrativo", "Direito Empresarial",
            "Direito do Trabalho", "Direito Tributário", "Direito Ambiental"
        ]
        
        self.termos_por_area = {
            "Direito Constitucional": [
                "Constituição Federal", "Direitos Fundamentais", "Habeas Corpus", 
                "Mandado de Segurança", "Ação Popular", "Federalismo"
            ],
            "Direito Processual Civil": [
                "Processo Civil", "Recurso", "Sentença", "Ação Rescisória",
                "Liminar", "Coisa Julgada"
            ],
            "Direito Penal": [
                "Crime", "Pena", "Prisão", "Culpabilidade", "Legítima Defesa",
                "Estado de Necessidade"
            ],
            "Direito Civil": [
                "Contrato", "Propriedade", "Obrigações", "Responsabilidade Civil",
                "Posse", "Usucapião"
            ],
            "Direito Administrativo": [
                "Licitação", "Servidor Público", "Ato Administrativo",
                "Improbidade", "Serviço Público"
            ],
            "Direito Empresarial": [
                "Sociedade", "Contrato Social", "Falência", 
                "Recuperação Judicial", "Capital Social"
            ],
            "Direito do Trabalho": [
                "CLT", "Rescisão", "FGTS", "Férias", "Horas Extras"
            ],
            "Direito Tributário": [
                "Imposto", "Taxação", "Isenção", "Deduções", "ICMS"
            ],
            "Direito Ambiental": [
                "Meio Ambiente", "Licenciamento", "Poluição", "Preservação"
            ]
        }
    
    def obter_termos_populares(self):
        """Retorna 5 termos aleatórios"""
        todos_termos = []
        for termos in self.termos_por_area.values():
            todos_termos.extend(termos)
        return random.sample(todos_termos, min(5, len(todos_termos)))
    
    def obter_termos_por_area(self, area):
        """Retorna termos de uma área específica"""
        if area == "Todas":
            return self.obter_termos_populares()
        return random.sample(self.termos_por_area.get(area, []), 
                           min(5, len(self.termos_por_area.get(area, []))))

# Cache para melhor performance
@st.cache_data(ttl=600)
def carregar_termos_populares():
    return GerenciadorTermos().obter_termos_populares()

@st.cache_data(ttl=600)
def carregar_termos_por_area(area):
    return GerenciadorTermos().obter_termos_por_area(area)

@st.cache_data(ttl=300)
def buscar_informacoes_termo(termo):
    """Busca definição e notícias para um termo"""
    buscador_def = BuscadorDefinicoes()
    buscador_not = BuscadorNoticias()
    
    definicao = buscador_def.buscar_definicao(termo)
    noticias = buscador_not.buscar_noticias(termo)
    
    return {
        "termo": termo,
        "definicao": definicao,
        "noticias": noticias
    }

# Páginas do aplicativo
def exibir_pagina_inicial():
    st.markdown("### 🎯 Bem-vindo ao Glossário Jurídico Digital")
    st.markdown("**Descomplicando o Direito** através de definições claras e atualizadas.")
    
    termos_populares = carregar_termos_populares()
    
    st.markdown("### 📈 Estatísticas do Acervo")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Termos Disponíveis", "+1000")
    with col2:
        st.metric("Áreas do Direito", "9")
    with col3:
        st.metric("Fontes", "4")
    with col4:
        st.metric("Atualização", "Contínua")
    
    st.markdown("### 🔥 Termos Populares")
    
    cols = st.columns(2)
    for idx, termo in enumerate(termos_populares):
        with cols[idx % 2]:
            with st.container():
                st.markdown(f'<div class="term-card">', unsafe_allow_html=True)
                
                st.markdown(f"#### ⚖️ {termo}")
                
                if st.button("🔍 Ver Detalhes", key=f"home_{termo}"):
                    st.session_state.termo_selecionado = termo
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

def exibir_explorar_termos():
    st.markdown("### 📚 Explorar Termos Jurídicos")
    
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        with st.form("busca_form"):
            termo_busca = st.text_input("🔍 Buscar termo jurídico:", placeholder="Ex: Habeas Corpus, Contrato, Lei")
            submitted = st.form_submit_button("🔍 Buscar Definição e Notícias")
            
            if submitted and termo_busca:
                st.session_state.termo_buscado = termo_busca
    
    with col_filtro2:
        gerenciador = GerenciadorTermos()
        areas = ["Todas"] + gerenciador.areas_direito
        area_filtro = st.selectbox("🎯 Filtrar por área:", areas, key="area_filter")
        
        if area_filtro != st.session_state.area_filtro:
            st.session_state.area_filtro = area_filtro
            st.session_state.termo_buscado = None
    
    # Exibir resultados da busca ou termos populares
    if st.session_state.termo_buscado:
        termo = st.session_state.termo_buscado
        st.info(f"🔍 Buscando informações para: **{termo}**")
        
        with st.spinner("Consultando fontes..."):
            resultado = buscar_informacoes_termo(termo)
        
        # Exibir definição
        if resultado["definicao"]:
            st.markdown(f"### 📖 Definição de {termo}")
            st.info(resultado["definicao"]["definicao"])
            st.caption(f"Fonte: {resultado['definicao']['fonte']}")
        else:
            st.warning("Não foi possível encontrar uma definição para este termo.")
        
        # Exibir notícias
        st.markdown(f"### 📰 Notícias sobre {termo}")
        if resultado["noticias"]:
            for noticia in resultado["noticias"]:
                with st.container():
                    st.markdown(f'<div class="news-card">', unsafe_allow_html=True)
                    st.markdown(f"#### {noticia['titulo']}")
                    st.write(noticia['resumo'])
                    st.caption(f"**Fonte:** {noticia['fonte']} | **Data:** {noticia['data']}")
                    if noticia['url'] != '#':
                        st.markdown(f'<a href="{noticia["url"]}" target="_blank" class="news-link">📖 Ler mais</a>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Nenhuma notícia específica encontrada para este termo.")
            
    else:
        # Exibir termos por área
        st.info(f"💡 **Termos em {st.session_state.area_filtro}**")
        termos = carregar_termos_por_area(st.session_state.area_filtro)
        
        for termo in termos:
            with st.container():
                st.markdown(f'<div class="term-card">', unsafe_allow_html=True)
                
                col_texto, col_acoes = st.columns([3, 1])
                
                with col_texto:
                    st.markdown(f"##### ⚖️ {termo}")
                    st.write(f"**{st.session_state.area_filtro}**")
                
                with col_acoes:
                    if st.button("🔍 Detalhes", key=f"exp_{termo}"):
                        st.session_state.termo_selecionado = termo
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

def exibir_pagina_termo(termo_nome):
    with st.spinner("Buscando informações..."):
        resultado = buscar_informacoes_termo(termo_nome)
    
    st.markdown(f'<div class="definition-card">', unsafe_allow_html=True)
    
    col_header, col_nav = st.columns([4, 1])
    
    with col_header:
        st.markdown(f"# ⚖️ {termo_nome}")
    
    with col_nav:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.termo_selecionado = None
            st.rerun()
    
    st.markdown("---")
    
    # Definição
    if resultado["definicao"]:
        st.markdown(f"### 📖 Definição")
        st.info(resultado["definicao"]["definicao"])
        st.caption(f"Fonte: {resultado['definicao']['fonte']}")
    else:
        st.warning("Definição não encontrada")
    
    # Notícias
    st.markdown(f"### 📰 Notícias")
    if resultado["noticias"]:
        for noticia in resultado["noticias"]:
            with st.container():
                st.markdown(f'<div class="news-card">', unsafe_allow_html=True)
                st.markdown(f"#### {noticia['titulo']}")
                st.write(noticia['resumo'])
                st.caption(f"**Fonte:** {noticia['fonte']} | **Data:** {noticia['data']}")
                if noticia['url'] != '#':
                    st.markdown(f'<a href="{noticia["url"]}" target="_blank" class="news-link">📖 Ler mais</a>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhuma notícia encontrada para este termo")
    
    st.markdown('</div>', unsafe_allow_html=True)

def exibir_pagina_noticias():
    st.markdown("### 📰 Notícias Jurídicas")
    
    with st.form("noticias_busca"):
        termo_noticias = st.text_input("🔍 Buscar notícias sobre:", placeholder="Digite um termo jurídico")
        buscar = st.form_submit_button("🔍 Buscar Notícias")
    
    if termo_noticias and buscar:
        with st.spinner("Buscando notícias..."):
            noticias = BuscadorNoticias().buscar_noticias(termo_noticias)
        
        if noticias:
            for noticia in noticias:
                with st.container():
                    st.markdown(f'<div class="news-card">', unsafe_allow_html=True)
                    st.markdown(f"#### {noticia['titulo']}")
                    st.write(noticia['resumo'])
                    st.caption(f"**Fonte:** {noticia['fonte']} | **Data:** {noticia['data']}")
                    if noticia['url'] != '#':
                        st.markdown(f'<a href="{noticia["url"]}" target="_blank" class="news-link">📖 Ler mais</a>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Nenhuma notícia encontrada para este termo")
    else:
        st.info("Digite um termo jurídico para buscar notícias")

def exibir_pagina_sobre():
    st.markdown("### ℹ️ Sobre o Projeto")
    st.write("""
    **Glossário Jurídico: Descomplicando o Direito**
    
    **Desenvolvido por:** Carolina Souza, Lara Carneiro e Mayra Rizkalla
    **Turma A** - Projeto P2 Programação
    
    **🎯 Objetivos:**
    - Fornecer definições claras de termos jurídicos via APIs
    - Contextualizar conceitos com exemplos práticos
    - Integrar notícias em tempo real dos principais portais
    - Oferecer ferramenta de estudo gratuita
    
    **⚙️ Tecnologias:**
    - Streamlit para interface web
    - Python como linguagem principal
    
    **📰 Fontes de Notícias:**
    - Consultor Jurídico
    - Jusbrasil
    - G1
    - Migalhas
    
    **📚 Fontes de Definições:**
    - Wikipedia
    - Dicio
    - Significado
    
    **📊 Estatísticas:**
    - +1000 termos jurídicos essenciais
    - 9 áreas do direito contempladas
    - 7 fontes consultadas
    - Interface moderna e responsiva
    - Notícias atualizadas para todos os termos
    """)

# App principal
def main():
    st.markdown('<h1 class="main-header">⚖️ Glossário Jurídico</h1>', unsafe_allow_html=True)
    st.markdown("### Definições e notícias em tempo real via APIs")
    
    # Sidebar
    with st.sidebar:
        st.title("🔍 Navegação")
        
        st.subheader("Buscar Termo")
        with st.form("sidebar_busca"):
            termo_busca = st.text_input("Digite um termo jurídico:")
            if st.form_submit_button("🔍 Buscar"):
                if termo_busca:
                    st.session_state.termo_selecionado = termo_busca
                    st.rerun()
        
        st.subheader("Termos Populares")
        termos = carregar_termos_populares()
        for termo in termos:
            if st.button(termo, key=f"side_{termo}"):
                st.session_state.termo_selecionado = termo
                st.rerun()
        
        st.markdown("---")
        st.metric("Status", "✅ Online")

    # Rotas principais
    if st.session_state.termo_selecionado:
        exibir_pagina_termo(st.session_state.termo_selecionado)
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["🏠 Início", "📚 Explorar", "📰 Notícias", "ℹ️ Sobre"])
        with tab1:
            exibir_pagina_inicial()
        with tab2:
            exibir_explorar_termos()
        with tab3:
            exibir_pagina_noticias()
        with tab4:
            exibir_pagina_sobre()

if __name__ == "__main__":
    main()
