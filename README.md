# 🥗 Nutrition Assistant (AI Systems Engineering Project)

## Overview

This project is an AI-powered Nutrition Assistant designed to help users with two main tasks:

- Estimating calories from food inputs (e.g., "apple 200g")
- Answering general nutrition-related questions

The system combines rule-based parsing, semantic retrieval, and memory mechanisms to provide reliable, explainable, and user-friendly responses.

This project was developed as part of the AI Systems Engineering course.

---

## Features

### 1. Calorie Estimation Mode
- Supports inputs like:
  - apple 200g
  - rice 150g and chicken 200g
  - apple200g (no spacing required)
- Matches food items against a nutrition database
- Computes total calories
- Provides per-item breakdown
- Includes:
  - confidence levels
  - coverage (matched vs total items)
  - suggestions when confidence is low

---

### 2. Nutrition Q&A Mode (RAG-based)
- Answers questions such as:
  - Is avocado healthy?
  - What are good sources of protein?
- Uses retrieval-based approach (no hallucinated answers)
- Shows:
  - retrieved contexts
  - source references
- Handles repeated questions using semantic memory

---

### 3. Meal Memory
- Keeps track of the current meal
- Supports follow-up inputs:
  - and banana 100g
- Allows:
  - incremental updates
  - clearing the meal
- Automatically updates total calories

---

### 4. Semantic Memory (Repeat Detection)
- Detects repeated questions
- Avoids recomputation
- Responds with:
  As I told you before...

---

### 5. Input Guard System
Handles edge cases such as:
- empty input
- non-English input
- missing food or quantity
- non-numeric quantities
- ambiguous or unclear text

---

## Architecture

The system follows a modular layered architecture:

src/
├── application/
│   ├── orchestrators/
│   ├── services/
│   │   ├── nlu/
│   │   ├── memory/
│   │   ├── resolver/
│   ├── use_cases/
│
├── domain/
│   ├── models/
│   ├── services/
│
├── infrastructure/
│   ├── vector_db/
│
├── presentation/
│   ├── chainlit_app.py
│
├── shared/

### Key Components
- NLU Service → normalization, parsing, intent classification  
- Orchestrator → routing between calorie and QA modes  
- Calorie Use Case → database-based estimation  
- QA Use Case → retrieval-based answers  
- Memory Services → meal memory + semantic memory  

---

## Datasets

### Calorie Dataset
- Source: Kaggle (Calories per 100g)
- Stored in ChromaDB
- Used for calorie estimation

### Nutrition Q&A Dataset
- Derived from a public nutrition dataset
- Stored as text blocks in ChromaDB
- Used for retrieval-based question answering

---

## Evaluation

The system was evaluated using multiple datasets:

- Standard evaluation
- Extended evaluation
- Randomized evaluation
- Adversarial evaluation

### Results

Category        | Pass Rate
---------------|----------
Calorie Mode   | 100%
Memory         | 100%
Multi-item     | 100%
Randomized     | 100%
Adversarial    | 96%
Overall        | ~99%

Evaluation focuses on:
- correctness
- robustness to noisy inputs
- memory behavior
- routing accuracy

---

## Example Inputs

apple 200g  
apple200g  
apple 200g rice 150g  
and banana 100g  
What are good sources of protein?  
Is avocado healthy?  

---

## How to Run

### Install dependencies
pip install -r requirements.txt

### Run the application
PYTHONPATH=. chainlit run src/presentation/chainlit_app.py -w

### Run evaluation
PYTHONPATH=. python scripts/run_eval.py  
PYTHONPATH=. python scripts/run_extended_eval.py  
PYTHONPATH=. python scripts/run_randomized_eval.py  
PYTHONPATH=. python scripts/run_adversarial_eval.py  

---

## Deployment

The system runs locally and can be containerized using Docker.

---

## Limitations

- Some noisy inputs may not extract all food items correctly  
- Repeated QA detection may fail in rare edge cases  
- Performance depends on dataset coverage  

---

## Future Improvements

- Improve parsing robustness for noisy inputs  
- Enhance QA memory reuse consistency  
- Expand nutrition dataset coverage  
- Add multilingual support  
- Improve UI/UX  

---

## Author

Fatemeh Niyavand 
University of Naples Federico II  

---

## Notes

This project focuses on:
- reliability  
- explainability  
- reproducibility  

rather than relying purely on black-box model outputs.