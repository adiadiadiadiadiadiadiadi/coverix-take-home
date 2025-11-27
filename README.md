The only .env variables you need are the OpenAI key and my Postgres DB's url, which is: 
SQLALCHEMY_DATABASE_URL='postgresql://chatbot_jejg_user:YAPqijll6gpt5jFjHFEXCrKfIVzQbSAw@dpg-d4jousruibrs73f0tps0-a.oregon-postgres.render.com/chatbot_jejg'.

Other than that, for setup, an npm install in the client and a pip install -r requirements.txt in the server is all that's needed for setup.

Server should run on port 8000. I would also run the client on port 3000, 3001, 3002, or 3003, as those are permitted through CORS policy for the backend. Let me know if you're unable to run the project!
