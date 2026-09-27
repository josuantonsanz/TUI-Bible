# Stylometry Analysis in OpenGNT

This document explains the mathematical and visual logic used for the stylometry analysis implemented in the project. The goal is to highlight words that are characteristic of each author or group of books in the New Testament.

## 1. Core Principles

The stylometry system is based on two fundamental metrics for each word:

1.  **Exclusivity**: How prevalent a word is in a given book/corpus compared to the "baseline" (the rest of the NT).
2.  **Significance**: A weighting factor that prevents low-frequency words from appearing as highly characteristic by chance.

### 1.1 Exclusivity Formula
The exclusivity ($X$) of a word with frequency $f_{book}$ compared to a baseline frequency $f_{baseline}$ is calculated as:

$$X = \frac{f_{book} - f_{baseline}}{f_{book}}$$

> [!NOTE]
> If $f_{book} \le f_{baseline}$, the exclusivity is 0.

### 1.2 Significance Formula
To weight the result, we use a saturation constant $K = 5.0$ (representing 5 occurrences per 10,000 words). The significance ($S$) is:

$$S = \frac{f_{book}}{f_{book} + K}$$

This ensures that a word appearing 100/10k is almost 100% significant, while one appearing 5/10k is 50% significant.

### 1.4 Reliability Factor ($R$)
To account for statistical noise in small books (e.g., 3 John with only 218 words), we apply a dampening factor based on the **absolute count ($c$)** of appearances:

- $c = 1 \implies R = 0.3$
- $c = 2 \implies R = 0.6$
- $c = 3 \implies R = 0.9$
- $c \ge 4 \implies R = 1.0$

The definitive intensity is then: $I_{final} = X \times S \times R$.

---

## 2. Stylometry Models

The project uses three distinct models depending on the book being read.

### 2.1 The Gospels Model (1D Comparative)
**Applied to**: Matthew (40), Mark (41), Luke (42), John (43).
**Logic**: Compares the frequency of a word among the four Gospels.

- **Baseline**: The frequency of the *second most frequent* Gospel for that word.
- **Exclusivity**: Calculated against that second-highest frequency.
- **Rendering**: Uses a single fixed color per Gospel with opacity proportional to the intensity $I$.
  - **Matthew**: Red (#e74c3c)
  - **Mark**: Green (#2ecc71)
  - **Luke**: Orange/Ochre (#e67e22)
  - **John**: Gold/Yellow (#f1c40f)

### 2.2 The Pauline & Johannine Models (2D Bivariate)
**Applied to**: 
- **Pauline**: Romans to Philemon (45-57).
- **Johannine**: 1-3 John and Revelation (62, 63, 64, 66). *Note: John's Gospel (43) provides data but uses the 1D Gospel colors.*

**Logic**: Uses a bivariate color model with two independent axes.
1.  **Blue Axis (Corpus Exclusivity)**: How characteristic the word is of the *entire corpus* (e.g., all of Paul) vs. the rest of the NT.
2.  **Yellow Axis (Internal Exclusivity)**: How characteristic the word is of *this specific book* (e.g., Romans) vs. the rest of the corpus.

**Colors**:
- **Pure Blue**: Typical of the author (e.g., typical of Paul everywhere).
- **Pure Yellow**: Typical of this specific book but not the rest of the author's work.
- **Green**: Highly typical of both (this book is where the author uses this characteristic word the most).

### 2.3 The Catholic Epistles Model (1D Exclusivity)
**Applied to**: Hebrews, James, 1-2 Peter, Jude (58-61, 65).
**Logic**: Simple 1D exclusivity for each individual book.
- **Baseline**: The highest average frequency of other major corpora (Gospels, Paulines, etc.).
- **Rendering**: Blue (#4a90e2) with opacity proportional to the intensity $I$.

---

## 3. The "Balanced Corpus Baseline" Refinement

One of the most critical refinements implemented is the **Balanced Corpus Baseline**. Instead of comparing against the global NT average, we compare against the *maximum average of other corpora*.

**Context**: 
A word like "ὑπομένω" appearing:
- 16/10k in **2 Timothy**
- 8/10k in **Hebrews**
- 11/10k in **James**

If we used the absolute peak (16) as a baseline, Hebrews and James would show 0 intensity.
With the **Balanced Baseline**, we use the *average frequency* of the other corpora as a floor. Since 8/10k in Hebrews is still significantly higher than the average frequency in the Pauline or Gospel groups, it still appears with a soft blue highlight, accurately reflecting its prevalence without being erased by a peak elsewhere.

---

## 4. Visual Representation Summary

| Corpus | Logic | Base Color | Meaning of Opacity |
| :--- | :--- | :--- | :--- |
| **Gospels** | 1D Internal | Matthew(Red), Mark(Green), Luke(Orange), John(Yellow) | Peak prevalence among the 4 Gospels. |
| **Pauline** | 2D Bivariate | Blue (Corpus) / Yellow (Internal) / Green (Both) | Blue = typical Paul; Yellow = unique to this book. |
| **Johannine** | 2D Bivariate | Blue (Corpus) / Yellow (Internal) / Green (Both) | Blue = Johannine style; Yellow = unique to this epistle/Rev. |
| **Catholic** | 1D Exclusivity | Blue | High prevalence compared to the rest of the NT corpora. |

---
*OpenGNT Stylometry Analysis System - Documentation updated March 2026*
