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
