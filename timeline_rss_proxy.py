
import urlparse
import oauth2 as oauth
import os


from bottle import route, run, response
import datetime
import json
import PyRSS2Gen


def setup():
    print 'Enter your consumer key: '
    _consumer_key = raw_input()
    print 'Enter your consumer secret: '
    _consumer_secret = raw_input()

    request_token_url = 'http://twitter.com/oauth/request_token'
    access_token_url = 'http://twitter.com/oauth/access_token'
    authorize_url = 'http://twitter.com/oauth/authorize'

    consumer = oauth.Consumer(_consumer_key, _consumer_secret)
    client = oauth.Client(consumer)

    # Step 1: Get a request token. This is a temporary token that is used for 
    # having the user authorize an access token and to sign the request to obtain 
    # said access token.

    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response %s." % resp['status'])

    request_token = dict(urlparse.parse_qsl(content))

    print "Request Token:"
    print "    - oauth_token        = %s" % request_token['oauth_token']
    print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
    print 

    # Step 2: Redirect to the provider. Since this is a CLI script we do not 
    # redirect. In a web application you would redirect the user to the URL
    # below.

    print "Go to the following link in your browser:"
    print "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])
    print 

    # After the user has granted access to you, the consumer, the provider will
    # redirect you to whatever URL you have told them to redirect to. You can 
    # usually define this in the oauth_callback argument as well.
    accepted = 'n'
    while accepted.lower() == 'n':
        accepted = raw_input('Have you authorized me? (y/n) ')
    oauth_verifier = raw_input('What is the PIN? ')

    # Step 3: Once the consumer has redirected the user back to the oauth_callback
    # URL you can request the access token the user has approved. You use the 
    # request token to sign this request. After this is done you throw away the
    # request token and use the access token returned. You should store this 
    # access token somewhere safe, like a database, for future use.
    token = oauth.Token(request_token['oauth_token'],
        request_token['oauth_token_secret'])
    token.set_verifier(oauth_verifier)
    client = oauth.Client(consumer, token)

    resp, content = client.request(access_token_url, "POST")
    access_token = dict(urlparse.parse_qsl(content))

    with open('secrets.py', 'w') as secret_file:
        secret_file.write('consumer_key = {0:r}'.format(_consumer_key))
        secret_file.write('consumer_secret = {0:r}'.format(_consumer_secret))
        secret_file.write('oauth_token = {0:r}'.format(access_token['token']))
        secret_file.write('oauth_token_secret = {0:r}'.format(
            access_token['token_secret']))


    token = oauth.Token(access_token['oauth_token'],
                        access_token['oauth_token_secret'])

try:
    from secrets import *
except ImportError:
    setup()
    from secrets import *

consumer = oauth.Consumer(consumer_key, consumer_secret)
token = oauth.Token(oauth_token, oauth_token_secret)
client = oauth.Client(consumer, token)

@route('/statuses/user_timeline/:name.rss')
def index(name):
    resp, content = client.request(
            'http://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=%s'
            % name,
            method='GET',
            )

    feed = json.loads(content)

    link_tmpl = 'http://twitter.com/{user}/status/{id}'

    rss = PyRSS2Gen.RSS2(
        title = 'Twitter / {0}'.format(name),
        link = 'http://twitter.com/{0}'.format(feed[0]['user']['name']),
        description = feed[0]['user']['description'],

        lastBuildDate = datetime.datetime.now(),

        items = [
           PyRSS2Gen.RSSItem(
             title = item['text'],
             link = link_tmpl.format(user=name, id=item['id']),
             description = item['text'],
             guid = PyRSS2Gen.Guid(link_tmpl.format(user=name, id=item['id'])),
             pubDate = datetime.datetime.strptime(
                 item['created_at'][:19] + item['created_at'][25:],
                 '%a %b %d %H:%M:%S %Y')
             ) for item in feed]
           )

    response.content_type = 'application/rss+xml; charset=latin9'
    return rss.to_xml()

run(host='localhost', port=8080)
