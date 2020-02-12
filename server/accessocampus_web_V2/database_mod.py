from app import db
from app.models import User, Post

users = User.query.all()
print(users)

q = input("New user? - yes/no")
if((q == "yes")):
    user = input("Username?")
    emaill = input("Email?")
    u = User(username=user, email=emaill)
    db.session.add(u)
    db.session.commit()
else:
    print("Using existing users...")

id = input("User id to add post?")
post_text = input("Post text?")
p = Post(body=post_text, author=User.query.get(id))
db.session.add(p)
db.session.commit()
