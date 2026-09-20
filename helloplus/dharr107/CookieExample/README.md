This is an example of a backend API using cookies to store user login information. However, this is only an example so data is only stored in memory and
disappears after the program stops running. 
# Steps to run
1. Run in terminal in file:
  python cookie.py
2. Create user:
   curl -X POST http://127.0.0.1:5000/register ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"alice\",\"password\":\"password123\"}"
3. Log in:
   curl -c cookies.txt -X POST http://127.0.0.1:5000/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"alice\",\"password\":\"password123\"}"
4. Check who's logged in:
   curl -b cookies.txt http://127.0.0.1:5000/me
5. Logout:
   curl -b cookies.txt -X POST http://127.0.0.1:5000/logout
