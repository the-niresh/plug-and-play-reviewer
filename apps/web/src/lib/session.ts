/** Matches LIVE_SIGN_IN_COOKIE_NAME in control_plane/github_oauth.py. The web app must
 *  not call the hosted API when this cookie is absent: without it the viewer is not
 *  signed in, and a dead control plane would otherwise look like a load failure. */
export const SIGN_IN_COOKIE_NAME = "gh_live_sign_in";

export function cookieHeaderHasSignIn(cookieHeader: string): boolean {
  if (!cookieHeader.trim()) {
    return false;
  }
  for (const part of cookieHeader.split(";")) {
    const trimmed = part.trim();
    if (!trimmed.startsWith(`${SIGN_IN_COOKIE_NAME}=`)) {
      continue;
    }
    const value = trimmed.slice(SIGN_IN_COOKIE_NAME.length + 1);
    return value.length > 0;
  }
  return false;
}
