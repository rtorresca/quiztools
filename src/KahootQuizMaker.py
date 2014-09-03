# -*- coding: utf-8 -*-

"""
Uses the python pacakge requests, see
http://docs.python-requests.org/en/latest/
"""

import json
import requests
import getpass
import re
import sys
import logging
from QuizMaker import QuizMaker

"""
___Kahoot syntax guide___

The 'quiz' object is used as input to upload_quiz, and as output from
get_quiz and get_quizzes with KahootQuizMaker. It is a python dictionary
with various key:value parameters. One of these keys are 'questions', which
should be a list of dictionaries corresponding to each question. 

___PARAMETERS___
title - string, title of the quiz
type - string, not in use, set it to 'quiz'
quizType - string, 'quiz'/'poll'/'survey'
visiblity - int, 0 is private, 1 is public
language - string, language of the quiz
description - string, metadata
audience - string, metadata
cover - string, url to cover image
        Note: images must be uploaded to kahoot servers
        when using the cover kwarg to make_quiz, give the local
        image file as string, and the method will upload it to
        the kahoot server and attach the url automatically

Question params
    question - string, question text
    questionFormat - int, 0 for image, 1 for video
    time - time for question in ms
    points - boolean, defines if the question is worth any points
    numberOfAnswers - int, from 2 to 4
    image - string, url to image (must be uploaded to kahoot servers)

    choices - list of dictionary
        answer - string, text of answer
        correct - boolean

    # Warning, video is an experimental feature
    video - dictionary, video to be shown in the background
        id - string, youtube-id
        startTime - int, in ms
        endTime - int, in ms, set to 0 to view to end
        service - "youtube", only supported service so feature

___EXAMPLE___
{
    'title': 'Quiz',
    'quizType': 'quiz',
    'type': 'quiz',
    'visibility': 0,
    'description': 'Made using quiztools.'
    'difficulty': 500,
    'audience': 'University',
    'language': 'English',

    'questions': 
    [{
        'question': u'What is the capital of Norway?',
        'points': True,
        'time': 60000,
        'numberOfAnswers': 4,
        'questionFormat': 0,
        'choices': 
        [{  
            'answer': u'Helsinki',
            'correct': False
        }, {
            'answer': u'Drammen',
            'correct': False
        }, {
            'answer': u'Oslo',
            'correct': True
        }, {
            'answer': u'Denmark',
            'correct': False
        }],
        'video': 
        {
            'service': 'youtube',
            'endTime': 0,
            'id': '',
            'startTime': 0
        },
    }, {
        'question': u'Which of the following cities are capitals?',
        'points': True,
        'time': 60000,
        'numberOfAnswers': 4,
        'questionFormat': 0
        'choices': 
        [{
            'answer': u'Sidney',
           'correct': False
        }, {
            'answer': u'Kigali',
            'correct': True
        }, {
            'answer': u'Bonn',
            'correct': False
        }, {
            'answer': u'Bern',
            'correct': True
        }, {
            'answer': u'Ottawa',
            'correct': True
        }, {
            'answer': u'New York',
            'correct': False
        }],
        'video': 
        {
            'service': 'youtube',
            'endTime': 0,
            'id': '',
            'startTime': 0
        },
    }],
}
"""

class KahootQuizMaker(QuizMaker):
    """
    Uses the Kahoot service. Register a user at getkahoot.com. Accesses
    your quizzes manually at create.kahoot.it to edit or play them.
    """
    def __init__(self, user, path="", force_new=False, loglvl=logging.WARNING):
        self.user = user 
        self.path = path
        logging.basicConfig(format='%(message)s', level=loglvl)

        # Get access token to be used in HTML requests
        self.login(force_new)


    def login(self, force_new=False):
        """Read access token from file or request new from server."""
        logging.info("Setting up access token."),
        user = self.user

        try:
            assert force_new == False
            with open(".%s_kahoot_token.txt" % user, "r") as f:
                self.token = f.readline()
            logging.info("Old token was sucsessfully read from file.")

        except:
            logging.info("Failed to find token locally," \
                         "requesting a new one from Kahoot servers.")
            password = getpass.getpass("Enter password for Kahoot-user %s: "
                                       % user)

            # Kahoot login server
            url = "http://db.kahoot.it/rest/authenticate"
            # Dictionary with login data
            authparams = {"username": user,
                          "password": password,
                          "grant_type": "password"}

            r = requests.post(url, data=json.dumps(authparams),
                              headers={"content-type":"application/json"})
            # Assert HTML status of response
            r.raise_for_status()

            # Fetch token from response object
            self.token = r.json()[u"access_token"]

            # Write access token to a file for future use
            with open(".%s_kahoot_token.txt" % user, "w") as f:
                f.write(self.token)
            logging.info("New token recieved from server and saved to file.")

        # Assert that connection works
        try:
            self.get_all_quizzes()
        except:
            logging.warning("Access denied. Token may be outdated." \
                            "Requesting new token from server.")
            self.login(self, force_new=True)


    def get_quiz(self, kahoot_id):
        """Fetch a given kahoot belonging to the user, returns dictionary."""
        logging.info("Fetching quiz %d from Kahoot servers." % kahoot_id),

        # URL for fetching specific kahoot
        url = "https://create.kahoot.it/rest/kahoots/%s" % kahoot_id

        r = requests.get(url, headers={
                         "content-type" : "application/json",
                         "authorization" : self.token})

        # Assert HTML status of response
        r.raise_for_status()
        logging.info("Quiz was fetched sucsessfully.")
        return r.json()

    def get_all_quizzes(self):
        """Fetch all kahoots belonging to user from server, return as list."""
        logging.info("Fetching all your quizzes from Kahoot servers.")

        # URL for fetching all quizzes
        url = "https://create.kahoot.it/rest/kahoots/browse/private?limit=30"

        r = requests.get(url, headers={
                         "content-type" : "application/json",
                         "authorization" : self.token})

        # Assert HTML status of response
        r.raise_for_status()
        logging.info("All quizzes returned successfully.")
        return r.json()[u"entities"]

    def upload_quiz(self, quiz):
        """Upload a quiz (python dictionary) to Kahoot, return url and id."""
        logging.info("Uploading quiz to kahoot.")

        # URL for making quizzes
        url = "http://db.kahoot.it/rest/kahoots"

        r = requests.post(url, data=json.dumps(quiz), headers={
                                "content-type" : "application/json",
                                "authorization" : self.token})

        # Assert HTML status of response
        r.raise_for_status()
        
        logging.info("Quiz successfully uploaded.")
        kahoot_id = r.json()["uuid"]
        return kahoot_id, self.fetch_url(kahoot_id)

    def fetch_url(self, kahoot_id):
        """Find url to access a certain quiz through a browser."""
        return r"https://play.kahoot.it/#/?quizId="+kahoot_id

    def delete_quiz(self, kahoot_id):
        """Delete kahoot of given id."""
        logging.info("Deleting quiz %d from Kahoot servers." % kahoot_id)

        # URL for deleting specific kahoot
        url = "https://create.kahoot.it/rest/kahoots/%s" % kahoot_id

        # HTML delete request
        r = requests.delete(url, headers={
                                "content-type" : "application/json",
                                "authorization" : self.token})

        # Assert HTML status
        r.raise_for_status()
        logging.info("Quiz successfully deleted.")

    def delete_all_quizzes(self):
        """Delete all kahoots on a given user."""
        print "This will delete ALL your quizzes, are you sure? (Y/n)"
        if raw_input("...").lower() != "y":
            logging.warning("Deletion aborted.")
            return

        quizzes = self.get_all_quizzes()
        for q in quizzes:
            self.delete_quiz(q["uuid"])

        logging.info("Kahoots deleted from user. User should now be clean.")

    def test_iframe(self, **kwargs):
        questions = \
        [{
            "question": "ee",
            "questionFormat": 2,
            "image": "",
            "time": 30000,
            "iframe": 
            {
                "content": "<html><head><script type='text/javascript' src='//cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML'></script></head><body> Compute the result of \\( a+b \\) in the case \\( a=2 \\) and \\( b=2 \\)."
            },
            "choices": [
            {
                "answer": "ee",
                "correct": False
            }, {
                "answer": "bb",
                "correct": True
            }],
            "points": True,
            "numberOfAnswers": 2
        }]

        # Add additional parameters
        # Default parameters
        quiz = \
        {
                 "title" : "Quiz",
                 "questions" : questions,
                 "quizType": "quiz",
                 "visibility": 1,  # 0: private, 1: public
                 "type": "quiz",
                 "difficulty": 500,
                 "audience": "University",
                 "language": "English",
                 "description": "Made using quiztools."
                }

        # User-given parameters
        for key in kwargs:
            if key == "cover":
                url = self.upload_image(kwargs["cover"])
                quiz["cover"] = url
            else:
                quiz[key] = kwargs[key]

        logging.info("Quiz-object successfully made.")
        return quiz




    def make_quiz(self, questions, **kwargs):
        """Take a list of dictionaries, return kahoot quiz dictionary."""
        logging.info("Turning questions into a Kahoot quiz object.")

        # Extract and modify questions
        for i, q in enumerate(questions):
            # Check for images in question text
            img_filenames = self.find_images(q["question"])
            if len(img_filenames) == 0:
                q["image"] = ""
            elif len(img_filenames) == 1:
                q["image"] = self.upload_image(img_filenames[0])
            else:
                q["image"] = self.upload_image(img_filenames[0])
                logging.warning("Warning: Question %i contains more than one"\
                    "image, only one of them have been uploaded" % i)

            # Remove HTML syntax from question text
            q["question"] = re.sub('<.*?>', '', q["question"])

            # Remove keys not relevant for Kahoot
            q.pop("no", None)
            q.pop("choice prefix", None)
            q.pop("question prefix", None)

            # Add choices
            for n, c in enumerate(q["choices"]):
                q["choices"][n] = {"answer" : c[1],
                    "correct" : c[0] == u"right"}

            # If there are more choices than 4, the rest are truncated
            if n+1 > 4:
                logging.warning("Warning: Kahoot only supports up to 4 answers"\
                    ", %i of the answers of question %i have been truncated!" \
                    % (n+1-4, i+1))

            # Additional question parameters
            q["numberOfAnswers"] = 4*(n+1 > 4) + (n+1)*(n+1 <= 4)
            q["questionFormat"] = 0
            q["time"] = 60000
            q["video"] = {"id" : "",
                          "startTime" : 0,
                          "endTime" : 0,
                          "service" : "youtube"}
            q["points"] = True
        # Add additional parameters
        # Default parameters
        quiz = {
                 "title" : "Quiz",
                 "questions" : questions,
                 "quizType": "quiz",
                 "visibility": 0,  # 0: private, 1: public
                 "type": "quiz",
                 "difficulty": 500,
                 "audience": "University",
                 "language": "English",
                 "description": "Made using quiztools."
                }

        # User-given parameters
        for key in kwargs:
            if key == "cover":
                url = self.upload_image(kwargs["cover"])
                quiz["cover"] = url
            else:
                quiz[key] = kwargs[key]

        logging.info("Quiz-object successfully made.")
        return quiz

    def upload_image(self, img_filename):
        """Take image filename, post image to kahoot server, return url."""
        logging.info("Uploading image to server.")

        with open(self.path+img_filename, "rb") as img:
            # URL for uploading media
            url = "https://create.kahoot.it/media-api/media/upload"

            img_type = img_filename.split(".")[-1]
            if img_type not in ["gif", "jpg", "png", "jpeg"]:
                logging.error("%s isn't a supported file-type for Kahoot.")
                logging.error("Make sure image file is png, jpg, jpeg or gif.")
                logging.error("Image has not been uploaded.")
                return ""

            files = {"f": (img_filename, img, "image/%s" % img_type)}
            r = requests.post(url, files=files, headers=
                             {"authorization" : self.token})

        # Assert HTML status
        r.raise_for_status()
        logging.info("Image successfully uploaded to kahoot server.")
        return r.json()["uri"]



if __name__ == "__main__":
    #### EXAMPLES USING Kahoot
    # Create QuizMaker-object
    qm = KahootQuizMaker("jvbrink", path="../demo-quiz/", loglvl=logging.INFO)

    # Example of reading .quiz file, then making and uploading a kahoot quiz
    #questions = qm.read_quiz_file(".test_jonas.quiz")
    #quiz = qm.make_quiz(questions, title='Test Quiz!')
    quiz = qm.test_iframe()
    kahoot_id, url = qm.upload_quiz(quiz)

    print "Uploaded quiz can be viewed at %s" % url

    # Example of fetching a pre-existing Kahoot
    #q = qm.get_all_quizzes()
    #kahoot_id =  q[0]["uuid"]
    #quiz = qm.get_quiz(kahoot_id)

    # Deleting all quizzes on users Kahoot page
    # qm.delete_all_quizzes()