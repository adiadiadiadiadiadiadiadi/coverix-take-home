The only .env variables you need are the OpenAI key and the Postgres DB's url.
Other than that, for setup, an npm install in the client and a pip install -r requirements.txt in the server is all that's needed for setup.

Server should run on port 8000. I would also run the client on port 3000, 3001, 3002, or 3003, as those are permitted through CORS policy for the backend. Let me know if you're unable to run the project!
