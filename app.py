from flask import Flask,request, redirect, render_template,flash,session # same as before
from flask_sqlalchemy import SQLAlchemy			# instead of mysqlconnection
from sqlalchemy.sql import func, and_,or_
from flask_migrate import Migrate			# this is new
from flask_bcrypt import Bcrypt
import re	# the regex module
from sqlalchemy import text
import json

# create a regular expression object that we'll use later   
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 

app = Flask(__name__)
bcrypt=Bcrypt(app)
app.secret_key="shush, no telling"

# configurations to tell our app about the database we'll be connecting to
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userbase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# an instance of the ORM
db = SQLAlchemy(app)
# a tool for allowing migrations/creation of tables
migrate = Migrate(app, db)

TWEET_LIMIT=5

# followers_table=db.Table('followers',
#     db.Column('user_id',db.Integer,db.ForeignKey('users.id'),primary_key=True),
#     db.Column('follower_id',db.Integer,db.ForeignKey('users.id'),primary_key=True),
#     db.Column('created_at',db.DateTime, server_default=func.now()),
#     db.Column('updated_at',db.DateTime, server_default=func.now(), onupdate=func.now()))
# found a way to make this work here: https://docs.sqlalchemy.org/en/latest/orm/join_conditions.html#self-referential-many-to-many


likes_table=db.Table('likes',
    db.Column('tweet_id',db.Integer,db.ForeignKey('tweets.id',ondelete="cascade"),primary_key=True),
    db.Column('user_id',db.Integer,db.ForeignKey('users.id'),primary_key=True),
    db.Column('created_at',db.DateTime, server_default=func.now()),
    db.Column('updated_at',db.DateTime, server_default=func.now(), onupdate=func.now()))

class User(db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True)
    first_name=db.Column(db.String(255))
    last_name=db.Column(db.String(255))
    email=db.Column(db.String(255))
    password=db.Column(db.String(255))
    user_level=db.Column(db.Integer)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    tweets_liked=db.relationship('Tweet', secondary=likes_table)
    #This line would be to use followers_table instead of class Follower:
    # followers=db.relationship('User',secondary=followers_table,primaryjoin="User.id==followers.user_id",secondaryjoin="User.id==followers.follower_id",backref="following")


class Follower(db.Model):
    __tablename__='followers'
    #id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,primary_key=True)
    follower_id=db.Column(db.Integer,primary_key=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    #follower=db.relationship('User',foreign_keys=[follower_id],primaryjoin="Follower.follower_id==User.id",backref="following")
    follower=db.relationship('User',foreign_keys=[follower_id],primaryjoin="Follower.follower_id==User.id",backref=db.backref("following",cascade="all,delete-orphan"))
    #user=db.relationship('User',foreign_keys=[user_id],primaryjoin="Follower.user_id==User.id",backref="followers")
    user=db.relationship('User',foreign_keys=[user_id],primaryjoin="Follower.user_id==User.id",backref=db.backref("followers",cascade="all,delete-orphan"))

class Tweet(db.Model):
    __tablename__='tweets'
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"), nullable=False)
    message=db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
    #add "tweets" to User class objects:
    #user=db.relationship('User',foreign_keys=[user_id],backref="tweets")
    user=db.relationship('User',foreign_keys=[user_id],backref=db.backref("tweets",cascade="all, delete-orphan"))
    liked_by=db.relationship('User',secondary=likes_table)

# class Like(db.Model):
#     __tablename__='likes'
#     id=db.Column(db.Integer, primary_key=True)
#     tweet_id=db.Column(db.Integer,nullable=False)
#     user_id=db.Column(db.Integer,nullable=False)
#     created_at = db.Column(db.DateTime, server_default=func.now())
#     updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

@app.route('/logout')
def logout_user():
    session.clear()
    return redirect('/')

@app.route('/')
def show_form():
    return render_template('register.html')

@app.route('/register',methods=["POST"])
def register_user():
    #validate name length
    errors=[]
    if len(request.form['first_name'])==0 or len(request.form['last_name'])==0:
        flash("Please enter your first and last names.",'registration')
        errors.append({"type":"name_error","message":"Please enter your first and last names."})
    if not request.form['first_name'].isalpha():
        flash("Names must be alphabet characters only!",'registration')
        errors.append({"type":"name_error","message":"Names must be alphabet characters only!"})
    #check name is not already in db
    existing_users=User.query.filter_by(first_name=request.form['first_name'], last_name=request.form['last_name']).all()
    #print("*"*80)
    #print(existing_users)
    if len(existing_users)>0:
        flash("This user's first and last name is already registered!",'registration')
        errors.append({"type":"name_error","message":"This user's first and last name is already registered!"})
    #validate password length, and match
    if len(request.form['password'])<5:
        flash("Password must be at least 5 characters long!",'registration')
        errors.append({"type":"password_error","message":"Password must be at least 5 characters long!"})
    if request.form['password']!=request.form['confirm_password']:
        flash("Passwords don't match!",'registration')
        errors.append({"type":"password_match_error","message":"Passwords don't match!"})
    #validate email pattern
    if not EMAIL_REGEX.match(request.form['email_address']):    # test whether a field matches the pattern
        flash("Invalid email address!",'registration')
        errors.append({"type":"emailMsg","message":"Invalid email address!"})
    #check email is not already in db
    existing_users=User.query.filter_by(email=request.form['email_address']).all()
    if (existing_users):
        flash("This email address is currently in use by another user!",'registration')
        errors.append({"type":"emailMsg","message":"This email address is currently in use by another user!"})
    if '_flashes' not in session.keys():
        hashed_pwd=bcrypt.generate_password_hash(request.form['password'])
        new_user=User(first_name=request.form['first_name'],last_name=request.form['last_name'],email=request.form['email_address'],password=hashed_pwd)
        db.session.add(new_user)
        db.session.commit()
        #print("#"*80)
        #print(new_user.id)
        session['MyWebsite_user_id']=new_user.id
        session['user_name']=request.form['first_name']+" "+request.form['last_name']
        return redirect('/success')
    e=json.dumps(errors)
    print(e)
    # return redirect('/')
    return e


@app.route('/success')
def login_success():
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    else:
        #return render_template('welcome.html')
        return redirect('/dashboard')

@app.route('/login',methods=['POST'])
def login_user():
    user_info=User.query.filter_by(email=request.form['email_address']).first()
    print("@"*80)
    print(user_info)
    if user_info:
        if bcrypt.check_password_hash(user_info.password,request.form['password']):
            session['MyWebsite_user_id']=user_info.id
            session['user_name']=user_info.first_name+" "+user_info.last_name
            #return redirect('/success')
            return "/success"
    # flash("Login failed: email or password is incorrect",'login')
    #return redirect('/')
    return "fail"

@app.route('/dashboard')
def user_dashboard():
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    else:
        u_id=session['MyWebsite_user_id']
        user=User.query.get(u_id)
        following_count=len(user.following)
        if 'tweet_count' not in session.keys():
            session['tweet_count']=TWEET_LIMIT
        tweets=Tweet.query.filter(or_(Tweet.user_id==user.id,Tweet.user_id.in_(db.session.query(Follower.user_id).filter(Follower.follower_id==user.id)))).order_by(Tweet.created_at.desc()).limit(session['tweet_count']).all()
        session['newest_tweet_id']=tweets[0].id
        session['oldest_tweet_id']=tweets[len(tweets)-1].id
        return render_template('dashboard.html',tweets=tweets,follow_count=following_count)

@app.route('/tweets/create',methods=['POST'])
def post_user_tweet():
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print('post user tweet')
    print(request.form['newtweet'])
    #print(session['MyWebsite_user_id'])
    if len(request.form['newtweet'])==0:
        flash("Type something in the Tweet Box, then click 'Submit'.")
        return redirect('/dashboard')
    #it appears unnessary to cast the session['user_id] str to an int
    new_tweet=Tweet(user_id=session['MyWebsite_user_id'],message=request.form['newtweet'])
    db.session.add(new_tweet)
    db.session.commit()
    return redirect('/dashboard')

@app.route('/tweets/<tweet_id>/delete',methods=['POST'])
def delete_tweet(tweet_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print('in delete_tweet')
    tweet=Tweet.query.get(tweet_id)
    if session['MyWebsite_user_id']==tweet.user_id:
        print('ok to delete')
        #deleting all the likes for this tweet is taken care of by the cascade in the foreign key constraint
        #delete the tweet
        db.session.delete(tweet)
        db.session.commit()
    return redirect('/dashboard')

@app.route('/tweets/<tweet_id>/add_like',methods=['POST'])
def like_tweet(tweet_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print('in like_tweet')
    user=User.query.get(session['MyWebsite_user_id'])
    tweet=Tweet.query.get(tweet_id)
    tweet.liked_by.append(user)
    db.session.commit()
    # return redirect('/dashboard')
    return str(len(tweet.liked_by))

@app.route('/tweets/<tweet_id>/edit')
def edit_tweet(tweet_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    #check user can edit this tweet
    print('in edit')
    tweet=Tweet.query.get(int(tweet_id))
    if tweet.user_id !=session['MyWebsite_user_id']:
        flash("No editing other peoples tweets!")
        return redirect('/dashboard')
    #print(tweet)
    return render_template('edit.html',tweet=tweet)

@app.route('/tweets/<tweet_id>/update',methods=['POST'])
def update_tweet(tweet_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print('in update')
    print(request.form)
    tweet=Tweet.query.get(tweet_id)
    if tweet.user_id !=session['MyWebsite_user_id']:
        flash("No editing other peoples tweets!")
    else:
        if len(request.form['edit_tweet'])==0:
            flash("To delete a tweet, Cancel and delete from the Dashboard.")
            return redirect('/tweets/'+tweet_id+'/edit')
        else:
            tweet.message=request.form['edit_tweet']
            db.session.commit()
    return redirect('/dashboard')

@app.route('/users',methods=['GET','POST'])
def show_users():
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    #create a list of users that are not the current user
    if request.method=='POST':
        users=User.query.filter(User.id!=(session['MyWebsite_user_id'])).filter(or_(User.first_name.like(request.form['search_string']+'%'),User.last_name.like(request.form['search_string']+'%'))).all()
        print(request.form['search_string'])
    else:
        users=User.query.filter(User.id!=(session['MyWebsite_user_id'])).all()
    #print("users: ",users)
    current_user=User.query.get(session['MyWebsite_user_id'])
    #create a list of user ids that the current_use is following
    following=[]
    for user_followed in current_user.following:
        following.append(user_followed.user_id)
    #print("following: ",following)
    #This kind of query returns a list of tuples of the specified columns.  Keeping it here as an example.
    #   f=db.session.query("followers.user_id").filter(Follower.follower_id==session['MyWebsite_user_id']).all()
    if request.method=='POST':
        return render_template('partials/usersearch.html',users=users,following=following)
    else:
        return render_template('users.html',users=users,following=following)

@app.route('/users/follow/<user_id>')
def follow_user(user_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print("follow user "+user_id)
    following=User.query.get(session['MyWebsite_user_id']).following
    following=db.session.query('followers.user_id').filter(Follower.follower_id==session['MyWebsite_user_id']).filter(Follower.user_id==user_id).all()
    print("following: ",following)
    if len(following)==0:
        new_follower=Follower(user_id=user_id,follower_id=session['MyWebsite_user_id'])
        db.session.add(new_follower)
        db.session.commit()
    return redirect('/users')

@app.route('/users/unfollow/<user_id>')
def unfollow_user(user_id):
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print("unfollow user "+user_id)
    #db.query_db('delete from followers where user_id=%(user_id)s and follower_id=%(follower_id)s;',follower_dict)
    #follow_to_delete=db.session.query(Follower).filter(Follower.user_id==user_id).filter(Follower.follower_id==session['MyWebsite_user_id']).first()
    follow_to_delete=Follower.query.filter_by(user_id=user_id,follower_id=session['MyWebsite_user_id']).first()
    print("follow_to_delete", follow_to_delete)
    db.session.delete(follow_to_delete)
    db.session.commit()
    return redirect('/users')


@app.route('/followers')
def show_followers():
    if 'MyWebsite_user_id' not in session.keys():
        return redirect('/')
    print("in followers of "+str(session['MyWebsite_user_id']))
    #followers=db.query_db('select concat(first_name, last_name) as follower_name, email from followers join users on users.id=followers.follower_id where user_id=%(user_id)s;',follower_dict)
    user=User.query.get(session['MyWebsite_user_id'])
    followers=user.followers
    for follower in followers:
        print("follower: ",follower.follower.email)
    return render_template('followers.html',followers=followers)

@app.route('/check_email',methods=['POST'])
def check_email():
    print(request.form)
    users=User.query.filter(User.email==request.form['email_address']).count()
    found=False
    if users>0:
        found=True
    #validate email pattern
    if EMAIL_REGEX.match(request.form['email_address']):    # test whether a field matches the pattern
        is_valid=True
    else:
        is_valid=False
    return render_template('partials/email.html',found=found,is_valid=is_valid)

@app.route('/getmoretweets',methods=['POST'])
def get_more_tweets():
    # print("get more tweets")
    # print(request.form)
    user=User.query.get(session['MyWebsite_user_id'])
    tweets=Tweet.query.filter(or_(Tweet.user_id==user.id,Tweet.user_id.in_(db.session.query(Follower.user_id).filter(Follower.follower_id==user.id)))).order_by(Tweet.created_at.desc()).offset(session['tweet_count']).limit(TWEET_LIMIT).all()
    if len(tweets)>0:
        session['tweet_count']+=len(tweets)
        session['oldest_tweet_id']=tweets[len(tweets)-1].id
        # for tweet in tweets:
        #     print(tweet.message)
    return render_template("/partials/moretweets.html",tweets=tweets)

@app.route('/poll_new_tweets',methods=['POST'])
def poll_for_tweets():
    user=User.query.get(session['MyWebsite_user_id'])
    tweets=Tweet.query.filter(or_(Tweet.user_id==user.id,Tweet.user_id.in_(db.session.query(Follower.user_id).filter(Follower.follower_id==user.id)))).filter(Tweet.id>session['newest_tweet_id']).order_by(Tweet.created_at.desc()).all()
    if len(tweets)>0:
        session['newest_tweet_id']=tweets[0].id
        session['tweet_count']+=len(tweets)
        return render_template("/partials/moretweets.html",tweets=tweets)
    return ""

if __name__=="__main__":
    app.run(debug=True)