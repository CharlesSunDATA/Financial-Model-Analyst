# import urllib.request as req
# url="https://www.ptt.cc/bbs/movie/index1.html"
# request=req.Request(url,headers={
#     "User-Agenr":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
#     })
# with req.urlopen(request) as response:
#     data=response.read().decode("utf-8")
# print(data)

import json
import urllib.request as req
import ssl

# 创建不验证 SSL 证书的上下文
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

url = "https://medium.com/_/graphql"

requestData=[{"operationName":"CuratedHomeFeedModuleQuery","variables":{"paging":{"from":"10","limit":10}},"query":"query CuratedHomeFeedModuleQuery($paging: PagingOptions!) {\n  staffPicksFeed(input: {paging: $paging}) {\n    items {\n      ...CuratedHomeFeedItems_homeFeedItems\n      __typename\n    }\n    pagingInfo {\n      next {\n        page\n        limit\n        from\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment CuratedHomeFeedItems_homeFeedItems on HomeFeedItem {\n  __typename\n  post {\n    id\n    title\n    ...HomeFeedItem_post\n    __typename\n  }\n}\n\nfragment HomeFeedItem_post on Post {\n  __typename\n  id\n  title\n  firstPublishedAt\n  mediumUrl\n  collection {\n    id\n    name\n    domain\n    logo {\n      id\n      __typename\n    }\n    __typename\n  }\n  creator {\n    id\n    name\n    username\n    imageId\n    mediumMemberAt\n    __typename\n  }\n  previewImage {\n    id\n    __typename\n  }\n  previewContent {\n    subtitle\n    __typename\n  }\n  readingTime\n  tags {\n    ...TopicPill_tag\n    __typename\n  }\n  ...BookmarkButton_post\n  ...OverflowMenuButton_post\n  ...PostPresentationTracker_post\n  ...PostPreviewAvatar_post\n  ...Star_post\n}\n\nfragment TopicPill_tag on Tag {\n  __typename\n  id\n  displayTitle\n  normalizedTagSlug\n}\n\nfragment BookmarkButton_post on Post {\n  visibility\n  ...SusiClickable_post\n  ...AddToCatalogBookmarkButton_post\n  __typename\n  id\n}\n\nfragment SusiClickable_post on Post {\n  id\n  mediumUrl\n  ...SusiContainer_post\n  __typename\n}\n\nfragment SusiContainer_post on Post {\n  id\n  __typename\n}\n\nfragment AddToCatalogBookmarkButton_post on Post {\n  ...AddToCatalogBase_post\n  __typename\n  id\n}\n\nfragment AddToCatalogBase_post on Post {\n  id\n  isPublished\n  ...SusiClickable_post\n  __typename\n}\n\nfragment OverflowMenuButton_post on Post {\n  id\n  visibility\n  ...OverflowMenu_post\n  __typename\n}\n\nfragment OverflowMenu_post on Post {\n  id\n  creator {\n    id\n    __typename\n  }\n  collection {\n    id\n    __typename\n  }\n  ...OverflowMenuItemUndoClaps_post\n  ...AddToCatalogBase_post\n  ...ExplicitSignalMenuOptions_post\n  __typename\n}\n\nfragment OverflowMenuItemUndoClaps_post on Post {\n  id\n  clapCount\n  ...ClapMutation_post\n  __typename\n}\n\nfragment ClapMutation_post on Post {\n  __typename\n  id\n  clapCount\n  ...MultiVoteCount_post\n}\n\nfragment MultiVoteCount_post on Post {\n  id\n  __typename\n}\n\nfragment ExplicitSignalMenuOptions_post on Post {\n  ...NegativeSignalModal_post\n  __typename\n  id\n}\n\nfragment NegativeSignalModal_post on Post {\n  id\n  creator {\n    ...NegativeSignalModal_publisher\n    viewerEdge {\n      id\n      isMuting\n      __typename\n    }\n    __typename\n    id\n  }\n  collection {\n    ...NegativeSignalModal_publisher\n    viewerEdge {\n      id\n      isMuting\n      __typename\n    }\n    __typename\n    id\n  }\n  __typename\n}\n\nfragment NegativeSignalModal_publisher on Publisher {\n  __typename\n  id\n  name\n}\n\nfragment PostPresentationTracker_post on Post {\n  id\n  visibility\n  previewContent {\n    isFullContent\n    __typename\n  }\n  collection {\n    id\n    slug\n    __typename\n  }\n  __typename\n}\n\nfragment PostPreviewAvatar_post on Post {\n  __typename\n  id\n  collection {\n    id\n    name\n    ...CollectionAvatar_collection\n    __typename\n  }\n  creator {\n    id\n    username\n    name\n    ...UserAvatar_user\n    ...userUrl_user\n    ...useIsVerifiedBookAuthor_user\n    __typename\n  }\n}\n\nfragment CollectionAvatar_collection on Collection {\n  name\n  avatar {\n    id\n    __typename\n  }\n  ...collectionUrl_collection\n  __typename\n  id\n}\n\nfragment collectionUrl_collection on Collection {\n  id\n  domain\n  slug\n  __typename\n}\n\nfragment UserAvatar_user on User {\n  __typename\n  id\n  imageId\n  mediumMemberAt\n  membership {\n    tier\n    __typename\n    id\n  }\n  name\n  username\n  ...userUrl_user\n}\n\nfragment userUrl_user on User {\n  __typename\n  id\n  customDomainState {\n    live {\n      domain\n      __typename\n    }\n    __typename\n  }\n  hasSubdomain\n  username\n}\n\nfragment useIsVerifiedBookAuthor_user on User {\n  verifications {\n    isBookAuthor\n    __typename\n  }\n  __typename\n  id\n}\n\nfragment Star_post on Post {\n  id\n  creator {\n    id\n    __typename\n  }\n  __typename\n}\n"}]
request = req.Request(url, headers={
    "content-Type":"application/json",
    "User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
},data=json.dumps(requestData).encode("utf-8"))

with req.urlopen(request, context=context) as response:
    result = response.read().decode("utf-8")
result=json.loads(result)
print(result[0]["data"]["staffPicksFeed"]["items"][0]["post"]["title"])
items=result[0]["data"]["staffPicksFeed"]["items"]
for item in items:
    print(item["post"]["title"])


#json





