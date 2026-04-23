# 🥗 Nutrition Assistant

An intelligent nutrition assistant that supports two main capabilities:

1. Calorie Estimation (structured input)
2. Nutrition Question Answering (RAG-based)

The system is designed with a clean architecture, strong evaluation coverage, and explainable outputs.

---

## 🎯 Project Goals

This project was designed to:

- Build a robust natural language interface for food tracking
- Combine structured estimation (calories) with unstructured QA (RAG)
- Ensure grounded, explainable outputs
- Maintain stateful interaction through meal memory
- Evaluate the system under standard, randomized, and adversarial conditions

The focus was not only on functionality, but also on reliability, interpretability, and evaluation.

---

## 🚀 Features

### 🍽️ Calorie Mode
- Accepts inputs like:
  - apple 200g
  - banana 100g and rice 150g
- Calculates total calories
- Maintains meal memory
- Supports:
  - Add items (and, add, with)
  - Remove items (remove apple)
  - Clear meal (clear meal)
- Provides:
  - Per-item breakdown
  - Total calories
  - Confidence score
  - Coverage (matched vs total items)

---

### 📚 Nutrition QA Mode (RAG)
- Answers questions like:
  - Is avocado healthy?
  - What are good sources of protein?
- Uses a nutrition Q&A dataset
- Retrieves relevant contexts
- Returns:
  - Answer
  - Confidence
  - Sources used
  - Retrieved context snippets

---

### 🧠 Memory & Repetition Handling
- Detects repeated questions
- Reuses previous answers when appropriate
- Supports meal memory for multi-turn calorie tracking

---

### ⚠️ Input Guard System
Handles invalid inputs:
- Empty input
- Non-English input
- Food without quantity
- Quantity without food
- Non-numeric quantities
- Gibberish input

---

## 🧱 Architecture

The project follows a clean, modular architecture:

src/
├── application/
│   ├── orchestrators/
│   ├── services/
│   ├── use_cases/
│   └── dto/
├── domain/
│   └── services/
├── infrastructure/
├── presentation/
│   └── chainlit_app.py
└── shared/

### Key Components

- NLU Service
  - Normalization
  - Parsing
  - Intent classification

- Orchestrator
  - Routes between Calorie Mode and QA Mode

- Meal Memory Service
  - Tracks current meal state

- Memory Service
  - Stores previous interactions

- RAG Pipeline
  - Retrieves and answers nutrition questions

---

## 📊 Evaluation Results

The system was evaluated using multiple datasets:

- Extended Evaluation: 99.5% pass rate
- Randomized Evaluation: 100% pass rate
- Adversarial Evaluation: 96% pass rate

These results demonstrate strong robustness, especially under noisy and adversarial inputs.

---

## 🔍 Explainability

Each calorie estimation includes:

- Match reason
- Match source
- Confidence level
- Coverage (matched items / total items)
- Suggestions for low-confidence matches

This ensures transparency and interpretability of results.

---

## ⚙️ Installation & Run

```bash
git clone https://github.com/your-username/nutritiona_ssistant.git
cd nutritiona_ssistant
pip install -r requirements.txt
export PYTHONPATH=.
chainlit run src/presentation/chainlit_app.py -w
```

---

## 🧪 Evaluation

```bash
PYTHONPATH=. python scripts/run_eval.py
PYTHONPATH=. python scripts/run_extended_eval.py
PYTHONPATH=. python scripts/run_randomized_eval.py
PYTHONPATH=. python scripts/run_adversarial_eval.py
```

---

## 💡 Example Usage

Calorie Mode:

```text
apple 200g
and banana 100g
```

QA Mode:

```text
Is avocado healthy?
What are good sources of protein?
```

---

## ⚠️ Limitations

- Noisy inputs may slightly reduce parsing accuracy in adversarial cases
- QA repeat detection depends on similarity thresholds
- Calorie database is static (no live updates)

---

## 🔮 Future Improvements

- Better handling of noisy and mixed inputs
- Integration with live nutrition APIs
- Personalized meal recommendations
- Advanced semantic matching

---

## 👩‍💻 Author

**Fatemeh Niyavand**  
MSc Data Science Student  
University of Naples Federico II

---

## 📌 Conclusion

This project demonstrates:

- Strong NLU design
- Robust routing between multiple modes
- Reliable evaluation performance
- Clear and explainable outputs

It is built to be both practical and academically solid.