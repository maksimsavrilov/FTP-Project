workspace "Hosting Control System" "Distributed hosting management system" {

    !identifiers hierarchical

    model {
        !include model/people.dsl

        hosting = softwareSystem "Hosting Control System" {
            !include model/cli.dsl
            !include model/master.dsl
            !include model/database.dsl
            !include model/agent-web.dsl
            !include model/agent-dns.dsl
            !include model/agent-mail.dsl
            !include model/agent-db.dsl

            description "CLI to REST API multi-node hosting control platform for Apache-Nginx + MySQL/PostgreSQL + Postfix-Courier/Qmail + Bind DNS"
            
        }

        !include model/relations.dsl

        admin -> hosting.cli "Uses" "Unix shell"
        reseller -> hosting.cli "Uses" "Unix shell"
        siteUser -> hosting.cli "Uses" "Unix shell"

        !include model/deployment.dsl
    }

    views {
        !include views/views.dsl
        !include views/styles.dsl
    }

    configuration {
        scope softwaresystem
    }

}
