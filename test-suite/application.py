from application_versions import AppVersion
from hawkeye_utils import hawkeye_request


class UnknownVersion(Exception):
  pass


class ImproperVersionsList(Exception):
  pass


class Application(object):
  """
  Application objects supposed to be used in test cases for hawkeye tests.
  It provides useful interface to AppScale application, so you can operate
  modules and version instead of specific IPs, host names and ports.

  It's based on requests library and is actually some kind of proxy for it.
  """

  def __init__(self, app_id, url_builder):
    self.app_id = app_id
    self._url_builder = url_builder

  def get(self, path, module=None, version=None, https=False, **kwargs):
    """
    Sends GET request to specified module and version of application.
    If module or version are missing, then default one will be used.

    Args:
      path: A string - path to http method. It can contain '{lang}'
        which will be replaced with application language.
      module: A string - identifies which module should be used.
      version: A string - identifies which version of module should be used.
      https: A boolean - determines if https should be used.
      kwargs: kwargs to be passed to requests.get function.
    Returns:
       request.Response object.
    """
    return self.request('get', path, module, version, https, **kwargs)

  def post(self, path, module=None, version=None, https=False, **kwargs):
    """
    Sends POST request to specified module and version of application.
    If module or version are missed, then default one will be used.

    Args:
      path: A string - path to http method. It can contain '{lang}'
        which will be replaced with application language.
      module: A string - identifies which module should be used.
      version: A string - identifies which version of module should be used.
      https: A boolean - determines if https should be used.
      kwargs: kwargs to be passed to requests.post function.
    Returns:
       request.Response object.
    """
    return self.request('post', path, module, version, https, **kwargs)

  def put(self, path, module=None, version=None, https=False, **kwargs):
    """
    Sends PUT request to specified module and version of application.
    If module or version are missed, then default one will be used.

    Args:
      path: A string - path to http method. It can contain '{lang}'
        which will be replaced with application language.
      module: A string - identifies which module should be used.
      version: A string - identifies which version of module should be used.
      https: A boolean - determines if https should be used.
      kwargs: kwargs to be passed to requests.put function.
    Returns:
       request.Response object.
    """
    return self.request('put', path, module, version, https, **kwargs)

  def delete(self, path, module=None, version=None, https=False, **kwargs):
    """
    Sends DELETE request to specified module and version of application.
    If module or version are missed, then default one will be used.

    Args:
      path: A string - path to http method. It can contain '{lang}'
        which will be replaced with application language.
      module: A string - identifies which module should be used.
      version: A string - identifies which version of module should be used.
      https: A boolean - determines if https should be used.
      kwargs: kwargs to be passed to requests.delete function.
    Returns:
       request.Response object.
    """
    return self.request('delete', path, module, version, https, **kwargs)

  def request(self, method, path, module=None, version=None,
              https=False, **kwargs):
    """
    Sends request to specified module and version of application.
    If module or version are missed, then default one will be used.

    Args:
      method: A string - represents HTTP methods.
      path: A string - path to http method. It can contain '{lang}'
        which will be replaced with application language.
      module: A string - identifies which module should be used.
      version: A string - identifies which version of module should be used.
      https: A boolean - determines if https should be used.
      kwargs: kwargs to be passed to requests.delete function.
    Returns:
       request.Response object.
    """
    url = self.build_url(path, module, version, https)
    return hawkeye_request(method, url, **kwargs)

  def build_url(self, path, module=None, version=None, https=True):
    """
    Like DNS returns IP for domain name, build_url returns full URL for
    module, version, path and schema (http/https).

    Args:
      path: A string - path to http method, it can contain '{lang}' which
        will be converted to current hawkeye language (shared.language)
        e.g.: /{lang}/product/add
      module: A string - module name; can be None if version is None,
        in this case default version of default module will be used).
      version: A string - version name; can be None,
        in this case default version of module will be used.
      https: A boolean - shows if https should be used instead of http.

    Returns:
      Full URL, e.g. "https://192.168.33.10:8082/api/product/add".
    """
    return self._url_builder.build_url(
      self.app_id, path, module, version, https)

  @property
  def language(self):
    return self._url_builder.language


class AppURLBuilder(object):
  """
  This class is responsible for building a URL
  from app_id, module, version, and path.

  It allows Application class to use modules and versions abstraction
  and not care about building specific URL.
  """

  def __init__(self, app_versions, language):
    """
    Args:
      app_versions: A list of AppVersion objects.
      language: A string - name of language which is currently being tested.
    """
    self.language = language

    # Find default versions for modules and globally for applications
    modules = {v.module for v in app_versions}
    module_default_versions = [
      v for v in app_versions if v.is_default_for_module
    ]
    app_default_versions = [
      v for v in module_default_versions if v.is_default_module
    ]

    # Verify if every single module has exactly one default version
    for m in modules:
      num_of_default = sum(1 for v in module_default_versions if v.module == m)
      if num_of_default != 1:
        raise ImproperVersionsList(
          "Module {} has {} default versions. Exactly 1 was expected"
          .format(m, num_of_default)
        )

    # Save version details into dict for a quick access
    self._versions_dict = {
      app_version.full_name: app_version for app_version in app_versions
    }

    # Add short links to module default versions
    self._versions_dict.update({
      AppVersion.get_version_alias(v.app_id, v.module): v
      for v in module_default_versions
    })

    # Add shorter links to application default versions
    self._versions_dict.update({
      AppVersion.get_version_alias(v.app_id): v
      for v in app_default_versions
    })

    # Finally self.versions_dict contains items like these:
    #       "old-version.moduleA.appX": <AppVersion objectA>,
    #   "default-version.moduleA.appX": <AppVersion objectB>,
    #                   "moduleA.appX": <AppVersion objectB>,
    #      "main-version.default.appX": <AppVersion objectC>,
    #                   "default.appX": <AppVersion objectC>,
    #                           "appX": <AppVersion objectC>

  def build_url(self, app_id, path, module, version, https):
    """
    Like DNS returns IP for domain name, build_url returns full URL for app_id,
    module, version, path and schema (http/https).

    Args:
      app_id: A string - application ID of running app.
      path: A string - path to http method, it can contain '{lang}' which
        will be converted to current hawkeye language (shared.language)
        e.g.: /{lang}/product/add
      module: A string - module name; can be None if version is None,
        in this case default version of default module will be used).
      version: A string - version name; can be None,
        in this case default version of module will be used.
      https: A boolean - shows if https should be used instead of http.

    Returns:
      Full URL, e.g. "https://192.168.33.10:8082/api/product/add".
    """
    # Allow testcases to leave a placeholder for language in path
    path = path.format(lang=self.language)

    # Get full (or short if module/version is None) name of specific version
    version_full_name = AppVersion.get_version_alias(app_id, module, version)

    app_version = self._versions_dict.get(version_full_name)
    if not app_version:
      known = sorted(self._versions_dict)
      raise UnknownVersion(
        "Unknown version '{v}' for module '{m}'. Available versions are:\n"
        "  {known}".format(v=version, m=module, known="\n  ".join(known))
      )

    if https:
      base_url = app_version.https_url
    else:
      base_url = app_version.http_url
    return "{base}/{path}".format(
      base=base_url.rstrip("/"), path=path.lstrip("/"))
