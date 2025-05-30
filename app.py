import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from llama_index.llms.groq import Groq
from llama_index.core.prompts import PromptTemplate
import time
import re
import os
import textwrap

@st.cache_resource
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_bin = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    driver_bin = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    chrome_options.binary_location = chrome_bin

    return webdriver.Chrome(executable_path=driver_bin, options=chrome_options)

def is_recent_article(date_text):
    recent_patterns = [r'minute[s]? ago', r'hour[s]? ago', r'1 day ago', r'yesterday', r'today']
    return any(re.search(pattern, date_text.lower()) for pattern in recent_patterns)

def search_google_news_latest(driver, query):
    formatted_query = query.replace(' ', '+')
    driver.get(f"https://www.google.com/search?q={formatted_query}&tbm=nws&tbs=sbd:1")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.SoaBEf")))
    
    news_results = []
    results = driver.find_elements(By.CSS_SELECTOR, "div.SoaBEf")
    for result in results:
        try:
            title = result.find_element(By.CSS_SELECTOR, "div.MBeuO").text
            link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            source = result.find_element(By.CSS_SELECTOR, ".NUnG9d span").text
            date = result.find_element(By.CSS_SELECTOR, ".LfVVr").text
            snippet = result.find_element(By.CSS_SELECTOR, ".GI74Re").text
            news_results.append({
                "title": title, "source": source, "date": date,
                "link": link, "snippet": snippet
            })
        except:
            continue
    return news_results

def extract_article_content(driver, url):
    try:
        driver.get(url)
        time.sleep(1)
        selectors = [
            "article", ".article-content", ".article-body", ".story-body",
            ".story-content", ".content-body", ".entry-content", "#content-body",
            ".post-content", ".main-content"
        ]
        content = ""
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                text = el.text.strip()
                if len(text) > 200:
                    content += text + "\n\n"
            if content:
                break
        if not content:
            paragraphs = driver.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                text = p.text.strip()
                if len(text) > 50:
                    content += text + "\n\n"
        return {"title": driver.title, "content": content, "url": url}
    except Exception as e:
        return {"title": "Error", "content": f"Failed to extract content: {e}", "url": url}

# === Streamlit UI ===
st.title("📰 News Summarizer with Groq LLaMA-3")
query = st.text_input("Enter your news topic (e.g., AI Regulation, Stock Market, etc.):")
submit = st.button("Fetch and Summarize News")

if submit and query:
    st.info("🔄 Launching browser and fetching news...")
    driver = setup_driver()

    try:
        news_results = search_google_news_latest(driver, query)
        st.success(f"✅ Found {len(news_results)} articles in total.")
        
        recent_articles = [a for a in news_results if is_recent_article(a['date'])]
        st.info(f"🕒 {len(recent_articles)} articles are from the last 24 hours.")
        if not recent_articles:
            st.warning("❌ No recent articles found.")
        else:
            all_content = f"# News: {query}\nSearch time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            summaries = []

            for i, article in enumerate(recent_articles, 1):
                st.write(f"📄 Extracting Article {i}: [{article['title']}]({article['link']})")
                data = extract_article_content(driver, article["link"])
                all_content += f"## {data['title']}\nSource: {article['source']}\nDate: {article['date']}\n\n{data['content']}\n\n{'='*80}\n\n"
                time.sleep(1)

            # === Summarize with LLaMA-3 ===
            st.info("🧠 Summarizing articles using LLaMA-3 via Groq...")

            # Set your Groq API Key securely
            api_key=os.getenv["GROQ_API_KEY"]
            llm = Groq(model="llama3-8b-8192",api_key=api_key)

            chunk_prompt = PromptTemplate(
                "Read the following news content and summarize it concisely. "
                "Focus on key events, trends, numbers, and noteworthy developments.\n\n{context_str}"
            )

            chunks = textwrap.wrap(all_content, width=3000)
            for chunk in chunks:
                prompt = chunk_prompt.format(context_str=chunk)
                response = llm.complete(prompt)
                summaries.append(response.text.strip())

            final_input = "\n\n".join(summaries)
            final_prompt = PromptTemplate(
                """You are a professional technical writer for a tech-savvy audience on LinkedIn.

Based on the following summaries of recent news articles, create a compelling LinkedIn-style post in exactly 200 words. Use the following format:

1. 🔥 Catchy Title
2. ✨ Short & engaging introduction
3. 📌 Key Highlights (bullet points)
4. 🧵 Closing remark
5. 📢 Add 5-7 trending hashtags

Tone: Professional, insightful, and engaging.

{context_str}
                """
            ).format(context_str=final_input)

            final_response = llm.complete(final_prompt)
            st.subheader("📢 LinkedIn-style Post Summary")
            st.text_area("Your 200-word Summary", final_response.text.strip(), height=300)

    except Exception as e:
        st.error(f"❌ Error occurred: {e}")
    finally:
        driver.quit()
