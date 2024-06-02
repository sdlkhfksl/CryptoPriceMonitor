name: Monitor Crypto Prices

on:
  schedule:
    - cron: '*/10 * * * *'  # Runs every 10 minutes
  workflow_dispatch:

jobs:
  run-monitor:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Setup Git
      run: |
        git config --global user.name "github-actions[bot]"
        git config --global user.email "github-actions[bot]@users.noreply.github.com"

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.8'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests python-dotenv

    - name: Load price history
      run: |
        git pull origin main
        if [ ! -f price_history.json ]; then
            echo "{}" > price_history.json
        fi

    - name: Run monitor script
      env:
        COINMARKETCAP_API_KEY: ${{ secrets.COINMARKETCAP_API_KEY }}
        CRYPTOCOMPARE_API_KEY: ${{ secrets.CRYPTOCOMPARE_API_KEY }}
        MESSARI_API_KEY: ${{ secrets.MESSARI_API_KEY }}
        TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      run: |
        python monitor_prices.py

    - name: Commit and Push changes
      env:
        ACTIONS_PAT: ${{ secrets.ACTIONS_PAT }}
      run: |
        git config --local user.email "github-actions[bot]@users.noreply.github.com"
        git config --local user.name "github-actions[bot]"
        git checkout --orphan latest_branch
        git add -A
        git commit -m "Update price history"
        git branch -D main
        git branch -m main
        git remote set-url origin https://x-access-token:${{ secrets.ACTIONS_PAT }}@github.com/${{ github.repository }}.git
        git push -f origin main
