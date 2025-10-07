import streamlit as st
from scrape_advanced import scrape_website_recursive, split_dom_content
from parse_advanced import parse_with_gemini, MODEL_NAME_FLASH
import time
import traceback
from io import BytesIO
import re

# Optional dependencies for visualization/export
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    VIS_AVAILABLE = True
except ImportError:
    VIS_AVAILABLE = False


st.set_page_config(page_title="SwiftScrape AI", layout="wide")
st.title("🕸️ SwiftScrape AI : Advanced LLM-Powered Web Scraper")

# --- ADVANCED SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🌐 Developer: [Subhan Basha](https://www.linkedin.com/in/subhanbasha/)")
    st.markdown("---")
    st.subheader("⚙️ Advanced Controls (Fast is MUST)")
    
    # Feature 1: Model Selection
    model_choice = st.selectbox(
        "Select AI Model:",
        options=[
            MODEL_NAME_FLASH, 
            "models/gemini-2.5-pro"
        ],
        format_func=lambda x: "Flash (Faster ⚡)" if "flash" in x else "Pro (Smarter, Slower)"
    )
    
    # Feature 2: Scraping Depth Control
    max_pages = st.slider("Max Pages to Scrape (Speed Control)", 1, 5, 2)
    polite_delay = st.slider("Politeness Delay (seconds)", 0.1, 2.0, 0.5, 0.1)

    st.markdown("---")
    st.warning("⚠️ **SETUP REQUIRED**\n\nSet your Gemini API key as an environment variable: `GEMINI_API_KEY`")


st.markdown("Paste a website link below and ask intelligent questions about its content.")

url = st.text_input("🔗 Enter Website URL")

if st.button(f"🚀 Scrape {max_pages} Pages & Analyze"):
    if url:
        # Clear previous state
        st.session_state.scraped_data = None
        st.session_state.qa_history = []
        st.session_state.all_text = "" # <-- FIX: Initialize variable

        with st.spinner(f"Scraping website... (Max {max_pages} pages)"):
            try:
                scraped_data = scrape_website_recursive(url, max_pages=max_pages, polite_delay=polite_delay)
                
                if scraped_data:
                    st.session_state.scraped_data = scraped_data
                    st.session_state.all_text = "\n\n".join(scraped_data.values())
                    st.success(f"✅ Website scraped successfully! ({len(scraped_data)} pages)")
                else:
                    st.warning("⚠️ No relevant content found.")
                    st.session_state.all_text = "" # Ensure it's empty if no data
            except Exception as e:
                st.error(f"❌ Scraping failed: {e}")
                with st.expander("🐛 Show Error Details"):
                    st.code(traceback.format_exc())
    else:
        st.warning("⚠️ Please enter a valid URL.")

# Ask questions
if "scraped_data" in st.session_state and st.session_state.scraped_data:
    st.subheader("💬 Ask Questions about the Website")
    
    # Feature 3: Raw Data Download - Safely accessed now
    # We check if 'all_text' exists and is not empty before showing the button
    if "all_text" in st.session_state and st.session_state.all_text: 
        st.download_button(
            "⬇️ Download Raw Scraped Data (TXT)",
            data=st.session_state.all_text,
            file_name="raw_scraped_data.txt",
            mime="text/plain",
            key='raw_download'
        )
    st.markdown("---")

    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []
    
    # Layout for question input
    user_question = st.text_area("❓ Ask something:", height=100, key="question_input")
    fetch_data = st.button("Get Answer")

    if user_question and fetch_data:
        try:
            # Combine all scraped text and split into chunks
            chunks = split_dom_content(st.session_state.all_text)

            # ✅ ULTRA FAST: Process all chunks in ONE API call using selected model
            with st.spinner(f"🔎 Analyzing content with {model_choice.split('/')[-1]}..."):
                start_time = time.time()
                answer = parse_with_gemini(chunks, user_question, model_choice)
                elapsed = time.time() - start_time
            
            if not answer or answer.strip() == "":
                answer = "No relevant information found in the scraped content."

            # Save Q&A in session
            st.session_state.qa_history.append((user_question, answer))

            # Show latest answer
            st.success(f"✅ Answer (processed in {elapsed:.1f}s):")
            st.write(answer) # Renders Markdown tables beautifully

            # --- PDF Export ---
            if PDF_AVAILABLE:
                def export_to_pdf(question, text):
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    title = Paragraph("SwiftScrape AI - Report", styles['Title'])
                    story.append(title)
                    story.append(Spacer(1, 12))
                    
                    q = Paragraph(f"<b>Question:</b> {question}", styles['Normal'])
                    story.append(q)
                    story.append(Spacer(1, 12))
                    
                    a_text = text.replace("\n", "<br/>")
                    a = Paragraph(f"<b>Answer:</b><br/>{a_text}", styles['Normal'])
                    story.append(a)
                    
                    doc.build(story)
                    buffer.seek(0)
                    return buffer

                pdf_buffer = export_to_pdf(user_question, answer)
                st.download_button(
                    "📄 Download Answer as PDF", 
                    pdf_buffer, 
                    file_name="swiftscrape_output.pdf",
                    mime="application/pdf",
                    key='pdf_download'
                )

            # --- Visualization attempt (For Price/Model Extraction) ---
            if VIS_AVAILABLE:
                try:
                    data = []
                    lines = answer.split("\n")
                    table_start = False
                    
                    for line in lines:
                        if line.startswith("|") and re.search(r"\|.*[Pp]rice.*\|.*[Mm]odel.*\|", line, re.IGNORECASE):
                            table_start = True # Found header row
                            continue
                        if table_start and re.match(r"\|-+\|", line):
                            continue # Skip separator line
                        if table_start and line.startswith("|"):
                            parts = [p.strip() for p in line.strip('|').split('|')]
                            
                            if len(parts) >= 2:
                                model_name_candidate = parts[0]
                                price_candidate = parts[-1].replace('$', '').replace('₹', '').replace(',', '').strip()
                                
                                if price_candidate.isdigit():
                                    data.append({"Model": model_name_candidate, "Price": int(price_candidate)})
                        elif table_start and not line.strip():
                            table_start = False # End of table
                        
                    if data:
                        df = pd.DataFrame(data).sort_values(by="Price", ascending=False)
                        st.subheader("📊 Visualization of Extracted Data")
                        
                        st.dataframe(df)

                        fig, ax = plt.subplots(figsize=(10, 6))
                        df.plot(kind="bar", x="Model", y="Price", ax=ax, legend=False, color="skyblue")
                        plt.xticks(rotation=45, ha="right")
                        plt.ylabel("Price (INR)")
                        plt.title("Extracted Prices")
                        plt.tight_layout()
                        st.pyplot(fig)
                        
                        # Add Chart Download
                        chart_buffer = BytesIO()
                        fig.savefig(chart_buffer, format='pdf')
                        chart_buffer.seek(0)
                        st.download_button(
                            "⬇️ Download Chart as PDF", 
                            chart_buffer, 
                            file_name="swiftscrape_chart.pdf",
                            mime="application/pdf",
                            key='chart_download'
                        )

                except Exception:
                    pass # Keep silent failure for cleaner user experience

        except Exception as e:
            st.error(f"❌ Failed to generate answer: {e}")
            with st.expander("🐛 Show Error Details"):
                st.code(traceback.format_exc())

    # Display past Q&A
    if st.session_state.qa_history:
        st.markdown("### 📝 Previous Questions & Answers")
        for idx, (q, a) in enumerate(reversed(st.session_state.qa_history)):
            q_num = len(st.session_state.qa_history) - idx
            with st.expander(f"Q{q_num}: {q[:60].strip()}..."):
                st.markdown(f"**Question:** {q}")
                st.markdown(f"**Answer:** {a}")

st.markdown("---")
st.markdown("Made by [Subhan Basha](https://www.linkedin.com/in/subhanbasha/) for **Batch-05 Minor Project**")