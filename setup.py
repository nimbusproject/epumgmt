import os
import tempfile
from setuptools import setup, find_packages

version = "0.0"

data_files = []

"""
Get files for etc from source, ensuring that we don't overwrite
any previously installed files. 
Also, make any path modifications neccessary for paths that are
typically hardcoded in etc
"""

etc_src_dir = "./etc/epumgmt/"
base_dst_dir = "~/.epumgmt/"

base_dst_dir = os.path.expanduser(base_dst_dir)
etc_dst_dir = os.path.join(base_dst_dir, "etc")
all_etc_files = os.listdir(etc_src_dir)

etc_files = []
for conf_file in all_etc_files:
    if not os.path.isfile(os.path.join(etc_dst_dir, conf_file)):
        etc_files.append(os.path.join(etc_src_dir, conf_file))

# Update var path to point to installed location
dirs_conf = os.path.join(etc_src_dir, "dirs.conf")
if dirs_conf in etc_files:
    tmp = tempfile.mkdtemp()
    new_dirs_conf = os.path.join(tmp, "dirs.conf")
    with open(dirs_conf) as dirs:
        with open(new_dirs_conf, "w") as new_dirs:
            dirs_str = dirs.read()
            dirs_str = dirs_str.replace("var/epumgmt/", base_dst_dir)
            new_dirs.write(dirs_str)
            dirs_idx = etc_files.index(dirs_conf)
            etc_files[dirs_idx] = new_dirs_conf

if etc_files:
    data_files.append((etc_dst_dir, etc_files))

"""
Get directories needed for var files
"""

var_src_dir = "./var/epumgmt/"
var_dirs = os.listdir(var_src_dir)
for var_dir in var_dirs:
    var_dir_dst = os.path.join(base_dst_dir, var_dir)
    keep_file = os.path.join(var_src_dir, var_dir, ".keep")
    data_files.append((var_dir_dst, [keep_file]))



src_root = "src/python"
setup(name="epumgmt",
      version = version,
      description = "EPU Management description placeholder",
      author = "Nimbus Development Team",
      author_email = "workspace-user@globus.org",
      url = "http://www.nimbusproject.org/",
      packages = find_packages(src_root, exclude="tests"),
      package_dir = {"": src_root},
      entry_points = {
          "console_scripts": [
              "epumgmt = epumgmt.main.em_cmdline:main"
          ]
      },
      dependency_links = ["https://github.com/nimbusproject/cloudyvents/tarball/master#egg=cloudyvents-0.1",
                          "https://github.com/nimbusproject/cloudminer/tarball/master#egg=cloudminer-0.2"],
      install_requires = ["cloudinitd ==  1.0rc1", "cloudyvents == 0.1", "cloudminer == 0.2"],
      data_files = data_files
)

