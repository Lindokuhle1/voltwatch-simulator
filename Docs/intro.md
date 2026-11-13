Project objective: Build a mini industrial battery telemetry platform that simulates how a real battery monitoring company collects, processes, stores and analyses battery data.

This is relevant to your industry experience, but it also demonstrates software engineering and data engineering skills.
1. Features to implement
Feature	What it demonstrates
Battery simulator	Generating realistic telemetry
REST API	Backend development
MQTT ingestion	IoT communication
Database storage	SQL and data modelling
Data validation	Data quality engineering
Battery analytics	Python and Pandas
Alerts engine	Business logic
Dashboard	Data visualisation

2. Proposed architecture
Battery Simulator

Voltage · Current · Temperature · SOC · SOH


Data Ingestion

MQTT Broker / Flask REST API


Validation

Missing values, duplicates, invalid readings


Processing

Calculations and enrichment




PostgreSQL Database

Raw telemetry · Clean telemetry · Battery records · Alerts


Analytics and Monitoring

Flask API · Dashboard · Battery health indicators · Alerts


3. Technology stack
I would use:
Layer	Technology
Programming	Python
Backend	Flask
Architecture	Clean Architecture
Messaging	Mosquitto MQTT
Database	PostgreSQL
Data processing	Pandas
Dashboard	React or Streamlit
Testing	Pytest
Version control	Git + GitHub
Deployment (later)	Azure

Don't try to implement everything at once. Get the ingestion, storage, processing and dashboard working first.
4. Weekend implementation plan
Saturday – 14 November
Backend and data engineering
- [ ] Create GitHub repository.
- [ ] Set up Flask using Clean Architecture.
- [ ] Create battery telemetry simulator.
- [ ] Implement MQTT or REST ingestion.
- [ ] Create PostgreSQL tables.
- [ ] Store raw telemetry.
- [ ] Implement data validation.


Sunday – 15 November
Analytics and presentation
- [ ] Calculate average voltage and current.
- [ ] Calculate battery SOC and temperature statistics.
- [ ] Implement abnormal-reading detection.
- [ ] Create battery monitoring dashboard.
- [ ] Write Pytest tests.
- [ ] Document architecture in README.md.
- [ ] Add screenshots and sample data to GitHub.


5. What your GitHub portfolio should demonstrate
By Sunday evening, aim to have:
- A working Python backend.
- A simulated telemetry source.
- A relational database.
- A functioning data pipeline.
- At least three battery analytics metrics.
- An alert mechanism.
- A dashboard with historical readings.
- Unit tests and technical documentation.
A recruiter should be able to clone your repository, follow your README and run the project.

Importantly, don't claim to have implemented predictive battery health estimation if you have only implemented threshold-based alerts. Keep the technical documentation accurate.
6. How I would position this on your CV
VoltWatch – Industrial Battery Telemetry and Analytics Platform

Technologies: Python, Flask, PostgreSQL, MQTT, Pandas, React, Pytest.

Developed an end-to-end IoT battery monitoring platform featuring simulated telemetry ingestion, data validation, structured storage, battery performance analytics and automated anomaly detection. Implemented a modular backend architecture and interactive monitoring dashboard.

This gives you portfolio evidence across three areas:
1. Software Engineering: Backend APIs, architecture, testing.
2. Data Engineering: Ingestion, transformation, validation and SQL.
3. Data Analytics: Battery performance, anomalies and visualisation.

7. Let's establish the project direction
My recommendation is to build VoltWatch rather than another standalone CRUD application. It gives you a practical demonstration of the intersection between your telematics experience and software development skills.
Choose your implementation approach

Frontend and backend

Flask + React (recommended)

Flask + Streamlit (faster)

Flask API only (backend focus)


Project scope

Weekend MVP

Production-style project


Database

PostgreSQL

SQLite

Start building VoltWatch
I can also help review your GitHub implementation on Sunday evening and identify what needs improving before you publish it.