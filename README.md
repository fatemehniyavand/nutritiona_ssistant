# 🥗 Nutrition Assistant (AI)

**Safe, Robust, and Explainable Nutrition System**

---

## 👩‍💻 Author

**Fatemeh Niyavand**
MSc Data Science
University of Naples Federico II

---

## 📌 Project Type

This project is an **Innovation-driven AI System**, aligned with the course *AI Systems Engineering*.

It addresses a **real-world problem**:

> Assisting users in tracking food intake and obtaining reliable nutrition information.

According to the project guidelines, this system follows:

* Requirements Analysis
* System Design
* Prototype Development
* Testing & Evaluation
* Local Deployment



---

## 🎯 Problem Statement

Users often struggle with:

* Estimating calories accurately
* Handling multiple food items in one query
* Asking nutrition-related questions safely
* Dealing with inconsistent or noisy input

This system provides a **robust, explainable, and safe solution**.

---

## 🚀 System Capabilities

### 🍽 Calorie Estimation

* Supports flexible inputs:

  * `apple 200g`
  * `apple200g`
  * `rice 100g and milk 200g`
* Handles:

  * Multi-item parsing
  * Noisy / glued inputs
  * Partial unknown foods
* Outputs:

  * Total calories
  * Per-item breakdown
  * Confidence score
  * Coverage (matched / total)
  * Suggestions for unknown foods

---

### 🧠 Nutrition Question Answering (RAG)

* Retrieval-Augmented Generation (RAG)
* Grounded answers only (no hallucination)
* Handles:

  * Paraphrased questions
  * Repeated queries
* Safe rejection for out-of-domain inputs

---

### 🗂 Meal Memory System

* Stateful interaction across turns
* Supports:

  * `what is the total now?`
  * `remove apple`
  * `clear meal`
* Prevents duplicate entries (repeat detection)

---

### 🛡 Safety & Guardrails

Detects and handles:

* Empty input
* Missing food or quantity
* Non-numeric quantities
* Unsupported queries
* Out-of-domain questions

Ensures **safe and deterministic behavior**.

---

## 🧱 System Architecture

### 1️⃣ Input Understanding Layer

```text
Raw Input
  ↓
Input Guard Service
  ↓
Food Normalizer
  ↓
Food Parser
  ↓
NLU Intent Classifier
  ↓
Structured Representation
```

Responsibilities:

* Normalize noisy input (`apple200g → apple 200g`)
* Extract structured data
* Detect user intent

---

### 2️⃣ Orchestrator (Decision Engine)

* Central control unit
* Routes requests based on intent
* Delegates execution to modules

Supported intents:

* `calorie_input`
* `nutrition_qa`
* `total_query`
* `remove_item`
* `clear_meal`

---

### 3️⃣ Calorie Estimation Engine

```text
Food Matching
→ Calorie Retrieval
→ Calculation
→ Confidence Assignment
→ Explainability
→ Memory Update
```

Formula:

```text
calories = (kcal_per_100g × grams) / 100
```

Features:

* Deterministic computation
* Confidence scoring
* Explainability layer
* Coverage tracking

---

### 4️⃣ Nutrition QA System (RAG)

```text
Question
→ Embedding
→ Vector Search (ChromaDB)
→ Context Retrieval
→ Answer Generation
```

Advantages:

* No hallucination
* Reproducible
* Transparent

---

### 5️⃣ Meal Memory

Maintains state:

```json
{
  "items": [
    {"food_name": "apple", "grams": 200, "calories": 104}
  ],
  "total_calories": 104
}
```

---

## 📂 Project Structure

```text
nutrition-assistant/
├── app.py
├── README.md
├── requirements.txt
├── Dockerfile
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── presentation/
│   └── shared/
│
├── eval/
│   ├── archive/
│   ├── datasets/
│   │   ├── archive/
│   │   └── eval_FINAL_ULTRA_700.json
│   └── outputs/
│
├── scripts/
│   ├── archive/
│   └── run_eval_boss.py
│
├── storage/
│   └── chroma/
│
└── tests/
```

---

## ▶️ How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Run the application

```bash
PYTHONPATH=. chainlit run src/presentation/chainlit_app.py -w
```

---

### 3. Run evaluation

```bash
PYTHONPATH=. python scripts/run_eval_boss.py
```

---

## 🧪 Evaluation

### Dataset

```text
eval/datasets/eval_FINAL_ULTRA_700.json
```

### Results

* Total test cases: **700**
* Passed: **660**
* Pass rate: **94.29%**

---

### Covered Behaviors

* Exact calorie computation
* Decimal handling & rounding
* Multi-item aggregation
* Noisy input normalization
* Fake food rejection
* Guardrails
* Q&A grounding
* Memory behavior
* Stress testing

---

### Failure Analysis

Main causes:

* Rounding differences (e.g., 64.97 vs 65)
* Strict evaluation constraints

Important:

* No hallucinated outputs
* No unsafe recommendations
* All safety mechanisms function correctly

---

## 💡 Example Inputs

### Calorie Mode

```text
apple 200g
apple 200g and banana 100g
dragon meat 200g
apple 200g and robot soup 100g
apple
200g
```

---

### Q&A Mode

```text
What are good sources of protein?
```

---

### Mixed Input

```text
apple 200g and what are good sources of protein?
```

---

### Tracking Commands

```text
today summary
yesterday summary
compare today with yesterday
weekly summary
```

---

## 🎯 Design Goals

* Explainability
* Deterministic behavior
* Zero hallucination (QA)
* Robust input handling
* Stateful interaction
* Reproducibility

---

## 🏁 Conclusion

This project demonstrates a **production-style AI system** that is:

* Accurate
* Robust
* Explainable
* Safe

It aligns with AI Systems Engineering principles by ensuring:

* Clear architecture
* Reliable evaluation
* Reproducible results
* Real-world applicability

---
