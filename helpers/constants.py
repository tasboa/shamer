class Constants():
  def __init__(self, source):
    # Source object
    self.source = source
    # Defaults
    self.defaults = {'EXPIRES': '300', 'GH_SCOPE': 'user,repo,read:org', 'MODE': 'redirect', 'HTTP': 'true'}

  def get(self, key, default=None):
    return self.source.get(key) or self.defaults.get(key, default)

  def set(self, key, value):
    self.source.set(key, value)

  def all(self, *args):
    try:
      return self.source.all(*args)
    except:
      raise
      return self.source
