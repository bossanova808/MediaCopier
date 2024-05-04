"""
Use this to grab the output from a system process.
If you want the output to go to screen instead, just use os.system("ls")

Example use:

from webtv_ripper import webtv_ripper

cmd_output = webtv_ripper(f'/usr/local/bin/yt-dlp -F {to_download} -S tbr')
print(cmd_output)

...gives a b'....' byte string

print(cmd_output.decode(sys.stdout.encoding))

... gives an actual string

# Looking for http-2125k-720p-0
quality = []
match = re.search(r"http-\d*k-720p-0", cmd_output.decode(sys.stdout.encoding))

"""

from subprocess import PIPE, Popen


def cmdline(command):
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return process.communicate()[0]
