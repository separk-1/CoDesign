# CoDesign — EBCT MVP
*A demo AI mediator for supporting design–engineering collaboration in water treatment systems (starting with EBCT calculation).*

---

## 🚀 Run Locally

Since Vercel’s serverless function size limits are not compatible with this project, you should run it locally.

### 1. Clone the repository
```bash
git clone https://github.com/separk-1/CoDesign.git
cd CoDesign
```

### 2. Create virtual environment and install dependencies
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment (optional)
Copy `.env.example` to `.env` and set environment variables if needed (e.g., `PORT`).

### 4. Run the Flask server
```bash
python app.py
```

The server will start at [http://127.0.0.1:5001](http://127.0.0.1:5001) by default.

### 5. Open the UI
Open `index.html` in your browser, or simply navigate to the server root:

```
http://127.0.0.1:5001/
```

This will show the EBCT Chat UI, where you can interact with the app.

---

## 💡 Usage Examples
Enter natural language queries:

- `flow 800 gpm, bed volume 9600 gal`
- `Tank diameter 10 ft, bed height 8 ft, flow 900 gpm`
- `what flow for 15 min`

---

## 📐 Calculation
- **EBCT(min)** = Volume(gal) / Flow(gal/min)  
- **Cylinder volume(ft³)** = π × (D/2)² × H  
- **Unit conversions**  
  - 1 ft³ = 7.48052 gal  
  - Supported units: gpm, L/min, m³/h / gal, ft³, m³ / ft, m, in  

---

## 🧭 Context
This MVP is part of the PITA project *“Automating PFAS Treatment and GAC System Design Refinement for Efficient Water Systems Operations and Maintenance”*.  
It demonstrates how AI mediators can structure communication and support EBCT calculations in design–engineering collaboration workflows.
