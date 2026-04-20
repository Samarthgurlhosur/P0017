# 🚀 Unified Anti-Corruption Platform

### AI-XBS + Transparency Fund System (Blockchain-Based)

---

## 📌 Overview

This project is a **Unified Anti-Corruption Platform** that combines:

* 💰 **Transparency Fund System**
* 🔍 **AI-XBS (AI-driven X-ray & Blockchain System)**

Both systems work independently but are integrated into a single web application to ensure **transparency, accountability, and security** in governance and inspection processes.

---

## 🧠 Core Idea

The platform eliminates corruption by:

* Tracking **public funds transparently**
* Detecting **illegal or suspicious items using AI**
* Recording all activities in **tamper-proof blockchain ledgers**

---

## 🏗️ System Architecture

```
project/
│
├── app.py
│
├── modules/
│   ├── fund_system/
│   │     ├── routes.py
│   │     ├── blockchain_fund.py
│   │
│   ├── ai_xbs/
│   │     ├── routes.py
│   │     ├── blockchain_xray.py
│   │     ├── image.py
│
├── templates/
├── static/
```

---

## 🔑 Key Features

### 💰 Transparency Fund System

* Track government fund allocation
* Milestone-based fund release
* Contractor and project management
* Fraud detection using Machine Learning
* Real-time notifications and alerts
* Dedicated blockchain for financial records

---

### 🔍 AI-XBS (AI X-Ray System)

* Real-time camera-based scanning
* Image upload and analysis
* Detection of:

  * Weapons 🔫
  * Explosives 💣
  * Contraband ⚠️
* Explainable AI (XAI):

  * Shows **what, where, and why**
* Dual-view scanning (normal + X-ray simulation)
* Separate blockchain for scan records

---

## 🔗 Blockchain Integration

The system uses **two independent blockchain ledgers**:

| System           | Purpose                       |
| ---------------- | ----------------------------- |
| Fund Blockchain  | Stores financial transactions |
| X-Ray Blockchain | Stores scan results           |

### Benefits:

* Tamper-proof records
* Transparency
* Decentralized validation
* Audit-ready logs

---

## ⚙️ Technologies Used

### Backend

* Python (Flask)
* Flask-SocketIO (real-time updates)
* OpenCV (image processing)
* NumPy

### AI / ML

* YOLO (object detection)
* Isolation Forest (fraud detection)
* Computer Vision

### Blockchain

* Custom blockchain implementation
* SHA-256 hashing
* Linked block structure

### Frontend

* HTML5, CSS3
* JavaScript
* Socket.IO

---

## 🌐 Routes Overview

| Route   | Description              |
| ------- | ------------------------ |
| `/fund` | Transparency Fund System |
| `/xray` | AI-XBS Scanner System    |

---

## ▶️ How to Run

### 1. Clone the repository

```
git clone <your-repo-url>
cd project
```

### 2. Create virtual environment

```
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Run the application

```
python app.py
```

### 5. Open in browser

```
http://localhost:5000
```

---

## 🧪 Example Use Cases

### 🏛 Government Monitoring

* Track fund usage
* Prevent misuse of public money

### ✈️ Security Checkpoints

* Detect illegal items automatically
* Store scan evidence securely

### 🔍 Auditing

* Verify transactions and scans using blockchain
* Ensure full transparency

---

## 🔒 Security Features

* Blockchain immutability
* Cryptographic hashing (SHA-256)
* Decentralized logic (conceptual)
* AI-based anomaly detection

---

## 🚀 Future Enhancements

* Real blockchain (Ethereum / Hyperledger)
* Face recognition integration
* Multi-user authentication system
* Cloud deployment (AWS / Render)
* Mobile app support

---

## 👨‍💻 Author

**Samarth**
Engineering Student | AI & Blockchain Enthusiast

---

## ⭐ Final Note

This project demonstrates how **AI + Blockchain** can be combined to build a **trustworthy, automated, and corruption-resistant ecosystem**.

---
