import pytube

url = input("Enter Url:")

path = ""

pytube.YouTube(url).streams.get_highest_resolution().download(path)

