# Project Setup Guide

This guide will walk you through setting up your development environment for this project, including creating a virtual environment, installing dependencies, setting up environment variables, and configuring MongoDB Atlas.

---

## 📦 Prerequisites

Ensure you have the following installed:

- [Python 3.8+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/)
- A code editor like [VS Code](https://code.visualstudio.com/)
- A [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account (free tier is sufficient)

---

## 🐍 Setting Up a Virtual Environment

1. **Create a virtual environment:**

   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**

   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

---

## 📥 Installing Dependencies

After activating the virtual environment, run:

```bash
pip install -r requirements.txt
```

This will install all the required packages listed in the `requirements.txt` file.

---

## 🔐 Setting Up Environment Variables

1. Create a `.env` file in the root directory of your project:

   ```bash
   touch .env
   ```

2. Add the following variables to your `.env` file:

   ```env
   MONGO_URI=your_mongodb_connection_uri
   SECRET_KEY=your_app_secret_key
   DEBUG=True
   ```

   Replace `your_mongodb_connection_uri` and `your_app_secret_key` with your actual values.

> You can use packages like `python-dotenv` or libraries like `pydantic` (in FastAPI) to load these environment variables.

---

## 🌐 Setting Up MongoDB Atlas and Getting a URI

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and sign in or create an account.
2. Click **"Build a Database"**, choose **Free Tier**, and follow the steps to create a cluster.
3. After the cluster is created:
   - Go to **Database Access** and add a new database user with a username and password.
   - Go to **Network Access** and add your IP address (or allow access from anywhere: `0.0.0.0/0`).
4. Click **Connect > Connect your application**, and copy the connection string.

   It will look like this:

   ```bash
   mongodb+srv://<username>:<password>@cluster0.mongodb.net/<dbname>?retryWrites=true&w=majority
   ```

5. Replace `<username>`, `<password>`, and `<dbname>` with your actual credentials and database name. Paste this into your `.env` file under `MONGO_URI`.

---

## ✅ You're Ready!

You can now run your app using:

```bash
python main.py
```

Or if you're using something like **FastAPI**, run:

```bash
uvicorn main:app --reload
```

---

Happy coding! 🚀
