import os, io, json, tempfile
import pandas as pd
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Voice → Excel Abstraction", page_icon="🎙️", layout="wide")
st.title("🎙️ Voice → Excel Clinical Abstraction")
st.caption("Prototype with synthetic or fully de-identified data only. Do not enter PHI without institutional approval and an appropriate agreement.")

DEFAULT_COLUMNS = ["Study ID","Age","Sex","Diagnosis","Diagnosis date","Stage","IPI","Treatment","Cycles","EOT PET response","MRD status","Residual clones/mL","Last follow-up","Relapse","Notes"]
if "rows" not in st.session_state: st.session_state.rows=[]
if "draft" not in st.session_state: st.session_state.draft=None
if "columns" not in st.session_state: st.session_state.columns=DEFAULT_COLUMNS.copy()

with st.sidebar:
    st.header("Setup")
    key=st.text_input("OpenAI API key", type="password", value=os.getenv("OPENAI_API_KEY",""))
    st.info("Use synthetic/de-identified information only. The API sends audio/text to an external service.")
    upload=st.file_uploader("Optional Excel template",type=["xlsx"])
    if upload:
        try:
            template=pd.read_excel(upload, nrows=0)
            cols=[str(c) for c in template.columns if not str(c).startswith("Unnamed")]
            if cols and cols != st.session_state.columns:
                st.session_state.columns=cols
                st.session_state.draft=None
        except Exception as e: st.error(f"Could not read template: {e}")
    st.write("Columns:", ", ".join(st.session_state.columns))
    if st.button("Reset all collected rows"):
        st.session_state.rows=[]
        st.session_state.draft=None
        st.rerun()

st.subheader("1. Dictate one patient")
audio=st.audio_input("Record your patient summary, then stop")
typed=st.text_area("Or paste/type the summary", height=130, placeholder="Study ID P023. Age 67, male, stage IV DLBCL, R-CHOP x6, MRD negative...")
if st.button("Extract fields",type="primary"):
    if not key: st.error("Enter an API key in the sidebar.")
    elif not audio and not typed.strip(): st.warning("Record audio or enter text first.")
    else:
        try:
            client=OpenAI(api_key=key)
            transcript=typed.strip()
            if audio:
                with st.spinner("Transcribing audio..."):
                    transcript=client.audio.transcriptions.create(
                        model="gpt-4o-mini-transcribe",
                        file=("recording.wav",audio.getvalue(),"audio/wav")
                    ).text
                if typed.strip(): transcript+="\nAdditional notes: "+typed.strip()
            st.session_state.transcript=transcript
            cols=st.session_state.columns
            with st.spinner("Matching dictation to Excel columns..."):
                resp=client.chat.completions.create(
                    model="gpt-4.1-mini",
                    response_format={"type":"json_object"},
                    messages=[
                        {"role":"system","content":(
                            "You are a clinical research data-entry assistant. Extract ONLY facts explicitly stated. "
                            "Do not infer, calculate, invent, or assume. Missing fields must be empty strings. "
                            "Return JSON with one key named 'fields', containing EXACTLY the supplied column names as keys, "
                            "each value a string. Preserve units. Do not substitute 'negative' for 'undetectable' unless stated. "
                            "If uncertain, leave blank and explain uncertainty in a key named 'warnings' (array of strings). "
                            "Never include information for a different patient."
                        )},
                        {"role":"user","content":json.dumps({"columns":cols,"dictation":transcript})}
                    ])
                result=json.loads(resp.choices[0].message.content)
            st.session_state.draft={c:str(result.get("fields",{}).get(c,"") or "") for c in cols}
            st.session_state.warnings=result.get("warnings",[])
        except Exception as e: st.error(f"Extraction failed: {e}")

if "transcript" in st.session_state:
    with st.expander("Transcript used for extraction",expanded=False):
        st.write(st.session_state.transcript)

if st.session_state.draft is not None:
    st.subheader("2. Review and correct before saving")
    if st.session_state.get("warnings"):
        st.warning("Review: "+"; ".join(map(str,st.session_state.warnings)))
    edited=st.data_editor(pd.DataFrame([st.session_state.draft]),hide_index=True,use_container_width=True,num_rows="fixed",key="draft_editor")
    if st.button("✓ Save patient row"):
        record={c:str(edited.iloc[0].get(c,"") or "") for c in st.session_state.columns}
        if not any(record.values()): st.warning("Cannot save an empty row.")
        elif not record.get("Study ID","").strip() and "Study ID" in record:
            st.warning("Please enter a Study ID before saving.")
        elif "Study ID" in record and any(r.get("Study ID")==record["Study ID"] for r in st.session_state.rows):
            st.error("Duplicate Study ID. Correct the identifier before saving.")
        else:
            st.session_state.rows.append(record)
            st.session_state.draft=None
            st.success("Row saved. Record the next patient.")
            st.rerun()

st.subheader("3. Collected rows")
df=pd.DataFrame(st.session_state.rows,columns=st.session_state.columns)
st.dataframe(df,use_container_width=True,hide_index=True)
output=io.BytesIO()
with pd.ExcelWriter(output,engine="openpyxl") as writer:
    df.to_excel(writer,index=False,sheet_name="Abstracted Data")
st.download_button("⬇ Download Excel workbook",data=output.getvalue(),file_name="abstracted_research_data.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.caption("Session data is held in memory and may be lost on refresh/restart. Download the workbook regularly.")
