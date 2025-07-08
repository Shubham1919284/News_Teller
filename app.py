from flask import Flask, render_template, request
import requests
import json
from config import NEWS_API_KEY
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from textblob import TextBlob
from datetime import datetime
import re

app = Flask(__name__)

# Load country ISO codes from JSON
with open("countries_dict.json", "r") as f:
    country_codes = json.load(f)

def clean_text(text):
    # Remove [+123 chars] artifacts and trim
    return re.sub(r"\[\+\d+\schars\]", "", text).strip()

def summarize_text(text, sentence_count=2):
    try:
        text = clean_text(text)
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, sentence_count)
        summary_text = " ".join(str(sentence) for sentence in summary)
        words = summary_text.split()
        if len(words) > 200:
            summary_text = " ".join(words[:200]) + "..."
        return summary_text
    except:
        return "Summary not available"

def get_sentiments(text):
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.1:
            return "🟢 Positive"
        elif polarity < -0.1:
            return "🔴 Negative"
        else:
            return "🟡 Neutral"
    except:
        return "Unknown"

@app.route("/", methods=["GET", "POST"])
def index():
    query = request.form.get("query")
    category = request.form.get("category")
    country_name = request.form.get("country") or "India"
    action = request.form.get("action")

    country_code = country_codes.get(country_name, "IN")

    articles = []
    search_title = None

    if action == "search" and query:
        search_title = f'Search Results for "{query}" ({country_name})'
        url = f"https://newsapi.org/v2/everything?q={query}+{country_name}&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        data = response.json()
        raw_articles = data.get("articles", [])

    elif action == "filter" and category:
        search_title = f'Top News in Category: "{category.title()}" ({country_name})'
        url = f"https://newsapi.org/v2/top-headlines?country={country_code}&category={category}&language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        data = response.json()
        raw_articles = data.get("articles", [])

        if not raw_articles:
            fallback_url = f"https://newsapi.org/v2/everything?q={category}+{country_name}&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
            response = requests.get(fallback_url)
            data = response.json()
            raw_articles = data.get("articles", [])

    else:
        url = f"https://newsapi.org/v2/top-headlines?country={country_code}&language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        data = response.json()
        raw_articles = data.get("articles", [])

    raw_articles = raw_articles[:10]

    for item in raw_articles:
        raw_text = item.get("description") or item.get("content") or ""
        content = clean_text(raw_text)

        summary = summarize_text(content)
        sentiment = get_sentiments(content)

        source = item.get("source", {}).get("name", "Unknown Source")
        published = item.get("publishedAt", "")
        try:
            published_dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
            published = published_dt.strftime("%d-%m-%Y %I:%M %p")
        except:
            published = "Unknown Time"

        articles.append({
            "title": item.get("title", "No Title"),
            "description": item.get("description", "No description available"),
            "url": item.get("url", "#"),
            "summary": summary,
            "sentiment": sentiment,
            "source": source,
            "published": published
        })

    return render_template("index.html", articles=articles, selected=category,
                           search_title=search_title,
                           country_list=country_codes.keys(),
                           selected_country=country_name)

if __name__ == '__main__':
    app.run(debug=True)
