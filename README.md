# Voice-to-Excel Research Abstraction — Prototype

## Start
1. Install Python 3.10+.
2. In a terminal, navigate to this folder.
3. Run `pip install -r requirements.txt`
4. Run `streamlit run app.py`
5. Enter an OpenAI API key in the sidebar.
6. Record one synthetic/de-identified patient summary or type it, click **Extract fields**, review/edit, and **Save patient row**.
7. Repeat; click **Download Excel workbook**.

You may upload an empty Excel template: the first row's column names define the abstraction schema. A sample template is included.

## Important limitations
- This is a working proof of concept, not a validated clinical system.
- Audio and transcript are sent to the OpenAI API. **Do not use identifiable patient information** without institution-approved controls, appropriate contracts/BAA, security review, and permitted data flows.
- The model may mis-transcribe or mis-extract; verify every field against the source record.
- No direct Epic integration, no automatic chart reading, no durable server-side database.
- Saved rows live in the browser's Streamlit session; download your workbook frequently.
- Uploaded templates provide columns, not original formatting or preexisting data.
- The app does not use the ChatGPT subscription; API billing is separate.
