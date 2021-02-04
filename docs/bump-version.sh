#!/usr/bin/env bash

REPOSITORY="arturtamborski/notion-py"
VERSION_FILE="notion/__init__.py"

[[ "$1" != @(major|minor|patch) ]] && {
    echo "./$0 <major|minor|patch>"
    exit 1
}
[[ "master" != "$(git branch | grep '\* ' | cut -c3-)" ]] && {
    echo "git says that you are not on master branch"
    echo "please checkout and run this script again :)"
    exit 1
}
git status | grep "not staged for commit" > /dev/null && {
    echo "git says that there are uncommitted changes"
    echo "please fix them and run this script again :)"
    exit 1
}

old_tag=$(git tag | tail -1)
old_num=$(echo "$old_tag" | cut -c2-)

major=$(echo "$old_num" | cut -d. -f1)
minor=$(echo "$old_num" | cut -d. -f2)
patch=$(echo "$old_num" | cut -d. -f3)

[[ "$1" == "major" ]] && major=$((major + 1))
[[ "$1" == "minor" ]] && minor=$((minor + 1))
[[ "$1" == "patch" ]] && patch=$((patch + 1))

new_num="$major.$minor.$patch"
new_tag="v$new_num"

echo "bumping  $old_num  to  $new_num"
sed --in-place "s/$old_num/$new_num/" "$VERSION_FILE"

echo "done"
echo "committing and pushing to origin"
git add "$VERSION_FILE"
git commit -m "'Release: $new_tag'"
git tag "$new_tag"

git push origin master
git push origin "$new_tag"

echo "done"
echo "creating release notes file"
refs=$(echo $(git show-ref --tags -s | tail -2) | sed 's/ /../')
diff=$(git log --oneline "$refs")

python3 > "$new_tag.md" <<EOF
from collections import defaultdict
commits = defaultdict(list)

for c in """$diff""".split("\n")[1:]:
    h, msg = c[:7], c[8:]
    mod, *msg = msg.split(": ")
    if not len(msg):
        msg, mod = [mod], "other"
    commits[mod.lower()].append((h, msg[0]))

for mod in sorted(commits):
    print(f"\n\n#### {mod}")
    for (h, m) in commits[mod]:
        print(f"{h}: {m}")

print("\n")
EOF

echo "done"
echo "publishing release notes on github"
new_tag_sha=$(git show-ref --tags -s | tail -1)

echo gh release create \
  --repo "$REPOSITORY" \
  --title "'Release: $new_tag'" \
  --notes-file "$new_tag.md" \
  --target "$new_tag_sha" \
  --draft

rm "$new_tag.md"
echo "all done, have a nice day :)"
