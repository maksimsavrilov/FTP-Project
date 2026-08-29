deploymentEnvironment "Production" {

    deploymentNode "Master Node" {
        masterInstance = containerInstance hosting.master
        databaseInstance = containerInstance hosting.database
    }

    deploymentNode "Worker Node" {
        webAgentInstance = containerInstance hosting.webAgent

        infrastructureNode nginxRuntime "nginx" {
            description "Web server managed by Web Agent"
            technology "nginx"
            -> webAgentInstance "Managed by"
        }

        infrastructureNode apacheRuntime "Apache" {
            description "Web server managed by Web Agent"
            technology "Apache HTTP Server"
            -> webAgentInstance "Managed by"
        }

        deploymentNode "DNS Agent" {
            containerInstance hosting.dnsAgent
        }

        deploymentNode "Mail Agent" {
            containerInstance hosting.mailAgent
        }
    }

    deploymentNode "Database Worker Node" {
        dbAgentInstance = containerInstance hosting.dbAgent
    }
}
