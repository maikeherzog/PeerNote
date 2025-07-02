from datetime import datetime
import uuid


class Card:
    def __init__(self, title, author, host, port):
        self.id = str(uuid.uuid4())
        self.title = title
        self.author = author
        self.timestamp: datetime = datetime.now()
        self.comments = {}
        self.votes = 0
        self.host = host
        self.content = ""
        self.port = port

    def get_id(self):
        return self.id

    def get_title(self):
        return self.title

    def update_timestamp(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_author(self):
        return self.author

    def get_content(self):
        return self.content

    def get_timestamp(self):
        return self.timestamp

    def get_all_comments(self):
        return list(self.comments.values())

    def get_votes(self):
        return self.votes

    def set_title(self, title):
        self.title = title

    def set_author(self, author):
        self.author = author

    def set_content(self, content):
        self.content = content

    def add_comment(self, comment):
        self.comments[comment.id] = comment

    def remove_comment(self, comment_id, comment_author):
        if comment_id in self.comments:
            if self.comments[comment_id].author == comment_author:
                del self.comments[comment_id]

    def upvote(self):
        self.votes += 1

    def downvote(self):
        if self.votes > 0:
            self.votes -= 1
