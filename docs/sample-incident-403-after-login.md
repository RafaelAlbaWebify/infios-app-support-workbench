# INFIOS M2 - HTTP 403 After Login

## Scenario

A user enters valid credentials, login succeeds, but the application returns HTTP 403 Forbidden when the user opens the dashboard.

This scenario is designed to practice Application Support triage around access-control failures after login.

## Support Focus

The goal is to separate:

- authentication: did the user prove their identity?
- session/token creation: did the application create or accept a valid session?
- authorization: does the user have the required role, group, claim, tenant/site scope, or app permission?
- application routing: is the requested page/resource restricted by route-level rules?

## Evidence To Collect

- exact timestamp;
- endpoint or route;
- HTTP status;
- correlation/request ID;
- browser observation;
- application authorization log;
- identity provider sign-in result;
- expected role/group/app permission;
- comparison with a known working user.

## Safe Boundaries

Do not add permissions, change groups, modify role mappings, restart services, or change production data without owner approval and evidence.

## Interview Explanation

> I added a second INFIOS scenario for HTTP 403 after login because it is a common Application Support problem. The important part is not to say "login is broken" too quickly. I separate successful authentication from authorization failure, then collect evidence around roles, groups, claims, route permissions, and application logs. This is closer to real support work because the user may be valid, but the application can still deny access after login.

