# Agile DevOps Assignment 2 – runbook

One app (Iris classifier, Flask) used for all three questions.

```
app.py                      Flask app: /  /health  /predict  /metrics
tests/test_app.py           pytest tests
Dockerfile, docker-compose  app + Prometheus + Grafana
.github/workflows/ci-cd.yml GitHub Actions: test -> docker build -> deploy
train.py                    MLflow training, model registry, "champion" alias
monitoring/                 prometheus.yml + Grafana datasource and dashboard (auto-provisioned)
docs/                       architecture.png / .dot, jira-tickets.md
```

Prometheus and Grafana run as containers from docker-compose, so nothing extra to install on Ubuntu.

---------------------------------------------------------------------

## 0. One-time setup in the project folder

```bash
cd ~/devops-assignment            # unzip the bundle here, so app.py sits directly inside
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -v               # screenshot: 5 passed
```

Create an empty GitHub repo (e.g. `agile-devops-assignment`, no README), then:

```bash
git init -b main
git add . && git commit -m "SCRUM-1 add Flask app, tests, Docker setup"
git remote add origin git@github.com:<your-github-username>/agile-devops-assignment.git
git push -u origin main
```

(The first push will run the workflow. The deploy job will wait until the runner in section Q1 step 4 exists.)

---------------------------------------------------------------------

## Q1 – CI/CD with GitHub Actions + Docker + Compose

1. Show the repo files and `.github/workflows/ci-cd.yml` on GitHub (screenshot).
2. Build and run locally:
   ```bash
   docker build -t iris-app:1.0 .
   docker images | grep iris-app           # screenshot
   ```
3. Deploy with Compose:
   ```bash
   docker compose up -d --build
   docker compose ps                       # screenshot: web, prometheus, grafana Up
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
        -d '{"inputs": [[5.1, 3.5, 1.4, 0.2]]}'
   ```
   Open http://localhost:8000 in the browser (screenshot).
4. Self-hosted runner (so the pipeline itself deploys on your machine):
   - GitHub repo -> Settings -> Actions -> Runners -> New self-hosted runner -> Linux x64.
   - Run the commands GitHub shows you (download, `./config.sh ...`), then start it: `./run.sh`
     (leave that terminal open).
   - Stop your manual stack first so ports are free: `docker compose down`
   - Push any small change; Actions tab -> the run shows Build and test -> Build Docker image -> Deploy (screenshot of the green run and of expanded steps).
   - `docker compose ps` again (screenshot): the pipeline started it.

## Q2 – MLflow lifecycle + Prometheus/Grafana

1. Install ML deps (venv active) and train three runs:
   ```bash
   pip install -r requirements-ml.txt
   python train.py
   ```
2. MLflow UI (new terminal, venv active):
   ```bash
   mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
   ```
   Open http://127.0.0.1:5000 and screenshot: Runs table (3 runs, different accuracy), a run's params and metrics, Models -> Iris_Classifier with versions 1, 2, 3 and the `champion` alias on the best one.
3. Deploy the registered model:
   ```bash
   MLFLOW_TRACKING_URI=sqlite:///mlflow.db \
   mlflow models serve -m "models:/Iris_Classifier@champion" -p 5001 --env-manager local
   ```
   In another terminal (screenshot both):
   ```bash
   curl http://127.0.0.1:5001/ping
   curl -X POST http://127.0.0.1:5001/invocations -H "Content-Type: application/json" \
        -d '{"inputs": [[5.1, 3.5, 1.4, 0.2]]}'
   ```
4. Monitoring (the stack from Q1 is already running; rebuild so the app uses the trained model):
   ```bash
   docker compose up -d --build
   for i in $(seq 1 40); do
     curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" \
          -d '{"inputs": [[5.1, 3.5, 1.4, 0.2]]}' > /dev/null
   done
   ```
   - Prometheus: http://localhost:9090/targets -> iris-app is UP (screenshot).
   - Grafana: http://localhost:3000 (login admin / admin, skip the password change) -> Dashboards -> "Iris App Monitoring" (screenshot). Re-run the curl loop if the panels are empty.

## Q3 – End-to-end pipeline

1. **Agile (Jira):** create the tickets from `docs/jira-tickets.md`, start a sprint. Screenshots: board with everything in To Do, board mid-sprint, board all Done.
2. **Git branching:** do one real change through a feature branch and PR:
   ```bash
   git checkout -b SCRUM-8-docs
   # edit README or app.py
   git add . && git commit -m "SCRUM-8 update documentation"
   git push -u origin SCRUM-8-docs
   ```
   On GitHub open a Pull Request into main (the test job runs on the PR; screenshot), then Merge (screenshot). The merge to main triggers test, build and deploy.
3. **CI/CD + deployment:** Actions run all green, `docker compose ps` (screenshots).
4. **Monitoring:** Prometheus targets UP, Grafana dashboard with traffic (screenshots).
5. **Architecture diagram:** `docs/architecture.png`. Put it in your report.

## Troubleshooting

- `permission denied` on docker: log out and back in once (docker group).
- Port already in use on 8000/9090/3000: `docker compose down`, or find the process with `sudo ss -ltnp | grep 8000`.
- Deploy job stuck "Waiting for a runner": the runner terminal (`./run.sh`) is not running.
- Grafana panels empty: send traffic with the curl loop, set the time range to "Last 15 minutes".
