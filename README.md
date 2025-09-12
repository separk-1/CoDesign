# EngSync — EBCT MVP
*A demo AI mediator for supporting design–engineering collaboration in water treatment systems (starting with EBCT calculation).*

---

## 🚀 Setup & Run

### 1. Create and activate a virtual environment
**venv**
```bash
python3 -m venv codesign
source codesign/bin/activate      # Mac/Linux
codesign\Scripts\activate       # Windows
```

**conda**
```bash
conda create -n codesign python=3.11 -y
conda activate codesign
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
Open **`index.html`** directly in your browser.  
(No server required — it runs locally.)

---

## 💡 Usage Examples
Type natural language queries:

- `EBCT? flow 800 gpm, bed volume 9600 gal`  
- `Tank diameter 10 ft, bed height 8 ft, flow 900 gpm`

---

## 📐 Calculation
- **EBCT(min)** = Volume(gal) / Flow(gal/min)  
- **Cylinder volume(ft³)** = π × (D/2)² × H  
- **Unit conversions**  
  - 1 ft³ = 7.48052 gal  
  - Supported units: gpm, L/min, m³/h / gal, ft³, m³ / ft, m, in  

---
