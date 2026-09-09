# Repository topics

GitHub topics are not stored in git. They are set on the repository in GitHub
settings or with the GitHub CLI.

## Maintainer checklist

Apply these topics on `the-niresh/plug-and-play-reviewer`:

- [ ] `code-review`
- [ ] `github-app`
- [ ] `python`
- [ ] `pull-requests`
- [ ] `self-hosted`
- [ ] `ai`
- [ ] `fastapi`
- [ ] `postgres`
- [ ] `security`

## Set topics with gh

You need admin access on the repository.

```bash
gh repo edit the-niresh/plug-and-play-reviewer \
  --add-topic code-review \
  --add-topic github-app \
  --add-topic python \
  --add-topic pull-requests \
  --add-topic self-hosted \
  --add-topic ai \
  --add-topic fastapi \
  --add-topic postgres \
  --add-topic security
```

Verify:

```bash
gh repo view the-niresh/plug-and-play-reviewer --json repositoryTopics --jq '.repositoryTopics[].name'
```

Topics can be removed with `--remove-topic` if a label no longer fits.
