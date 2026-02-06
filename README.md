# SalesSpark AI - Quick Start Guide

## 1. Prerequisites
- Python installed
- A terminal (Command Prompt, PowerShell, or VS Code Terminal)

## 2. Setup (One Time Only)
Open a terminal in the project folder `C:\Users\tolet\TeamXspark` and run:
```bash
pip install -r requirements.txt
```

## 3. Run the "Brain" (Backend)
In the same terminal, run:
```bash
uvicorn backend.main:app --reload
```
**Effect:** You will see "Application startup complete".
**Important:** Do NOT close this terminal. The AI needs this running to work.

## 4. Run the "Face" (Frontend)
1. Go to your project folder using File Explorer.
2. Double-click `index.html` to open it in Chrome/Edge.
   *OR*
   If you use VS Code, right-click `index.html` and select "Open with Live Server".

## 5. Test It
1. Go to **AI Tools** page.
2. Generate a Campaign.
3. Go to **Dashboard**.
4. You should see the "Total Campaigns" counter go up!
