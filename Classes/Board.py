import socket
import threading
import json
import hashlib
import time
from datetime import datetime
import uuid
import random

class Board:
  def __init__(self, title, keywords):

    self.board_id = str(uuid.uuid4())
    self.title = title
    self.keywords = keywords
    self.card_references = {}
    self.not_allowed_to_write = []

  def get_board_id(self):
    return self.board_id

  def get_title(self):
    return self.title

  def get_keywords(self):
    return self.keywords

  def get_card_references(self):
    return self.card_references

  def get_not_allowed_to_write(self):
    return self.not_allowed_to_write



  def set_title(self, title):
    self.title = title

  def set_keywords(self, keywords):
    self.keywords.extend(keywords)

  def add_card_reference(self, card_id, peer_id, peer_host, peer_port):
    if peer_id not in self.card_references:
      self.card_references[card_id] = (peer_host, peer_port)

  def add_not_allowed_to_write(self, user_id):
    self.not_allowed_to_write.append(user_id)