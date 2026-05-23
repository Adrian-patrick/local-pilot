# Making Local Pilot Show As Yours On GitHub

There are two different things people usually mean by "show as mine":

## 1. Your commits show as yours

This repo is already configured locally as:

```text
Hitan K <hitank2004@gmail.com>
```

If that email is verified on your GitHub account, commits you push will show under your profile.

## 2. The repository itself appears under your account

If the repo is owned by `Adrian-patrick/local-pilot`, the clean options are:

- Ask Adrian to transfer ownership to your GitHub account.
- Fork the repo to your account and work from your fork.
- Keep collaborating on Adrian's repo, where your commits and pull requests still show as your work.

Do not rewrite authorship to hide Adrian's work. Keep the history clean and add yourself as an author through your own commits.

## Recommended Setup

For a friend-created repo, the healthiest workflow is:

1. Keep `origin` pointing to Adrian's repo if you are both collaborating there.
2. Create feature branches for your work.
3. Push your branch.
4. Open pull requests from your branch.

If you want a copy under your own profile too, fork it on GitHub and add it as a second remote:

```bash
git remote add myfork https://github.com/YOUR_USERNAME/local-pilot.git
git push -u myfork stage-1-mvp-scaffold
```

