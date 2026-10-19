# 🏈 Fantasy Football Waiver & FAAB Optimizer

A real-time Streamlit web application that syncs with the Sleeper API to track trending waiver wire activity, analyze your league rosters, and provide data-driven FAAB bidding suggestions or waiver priority tiers.

## 🚀 Features

* **Sleeper API Integration:** Automatically fetches live player databases and trending add/drop data.
* **League Sync:** Input your Sleeper username to select your league, inspect your roster breakdown by position, and see which players are already rostered.
* **Smart Detection:** Automatically detects whether your league uses FAAB (Free Agent Acquisition Budget) or Waiver Priority.
* **Custom Recommendation Engine:** Calculates target ratings and suggests optimized dollar bids or priority tiers based on market velocity and player position value.

---

## 🛠️ Tech Stack

* **Python**
* **Streamlit** (Frontend UI & Charts)
* **Pandas & NumPy** (Data processing & calculations)
* **Requests** (Sleeper REST API integration)

---

## ⚙️ How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/btbtbrady/Faab_Optimizer.git](https://github.com/btbtbrady/Faab_Optimizer.git)
   cd Faab_Optimizer