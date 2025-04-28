def clean_url(url: str):
    url = url.split("#")[0]
    url = url.replace("http://", "https://")
    url = url.replace("www.", "")
    # fix a specific problem in test set
    url = url.replace("/download?inline", "")
    url = url.replace("%20", " ")

    return url
