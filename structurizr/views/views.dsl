systemContext hosting "SystemContext" {
    include admin
    include reseller
    include siteUser
    include hosting
    autolayout lr
}

container hosting "Containers" {
    include *
    autolayout lr
}

deployment hosting "Production" {
    include *
    autolayout lr
}

component hosting.master "MasterComponents" {
    include *
    autolayout lr
}

component hosting.webAgent "WebAgentComponents" {
   include *
   autolayout lr
}

component hosting.dnsAgent "DnsAgentComponents" {
   include *
   autolayout lr
}

component hosting.mailAgent "MailAgentComponents" {
   include *
   autolayout lr
}

component hosting.dbAgent "DbAgentComponents" {
   include *
   autolayout lr
}

!include dynamic-node-registration-web.dsl
!include dynamic-node-registration-db.dsl
!include dynamic-user-creation.dsl
!include dynamic-hosting-plan-creation.dsl
!include dynamic-subscription-creation.dsl
!include dynamic-service-creation.dsl
!include dynamic-node-monitoring.dsl