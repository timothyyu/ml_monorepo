echo "create a datascience heroku environment incrementally; can't push all requirements at once (time out)"
# https://github.com/thenovices/heroku-buildpack-scipy
heroku login # heroku auth:login --app APPNAME

echo "create base heruko app"
git clone https://github.com/heroku/python-getting-started.git datascience
cd datascience
heroku create --buildpack https://github.com/thenovices/heroku-buildpack-scipy
git push heroku master

echo "add numpy and scipy"
echo -e "numpy==1.8.1\nscipy==0.14.0" >> requirements.txt
git add requirements.txt
git commit -m 'Added numpy and scipy'

echo "add pandas and matplotlib"
echo -e "pandas==0.16.0\nmatplotlib==1.4.0" >> requirements.txt
git commit -a -m 'Added pandas and matplotlib'
git push heroku master

echo "add sklearn"
echo -e "scikit-learn==0.16.0\ntheano==0.7.0" >> requirements.txt
git commit -a -m 'Added ML libs'
git push heroku master

echo "try it"
# open browser
heroku open
# check c
heroku run python manage.py shell


