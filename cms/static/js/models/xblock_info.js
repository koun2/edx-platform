define(["backbone", "underscore", "js/utils/module"], function(Backbone, _, ModuleUtils) {
    var XBlockInfo = Backbone.Model.extend({

        urlRoot: ModuleUtils.urlRoot,

        // NOTE: 'publish' is not an attribute on XBlockInfo, but it is used to signal the publish
        // and discard changes actions. Therefore 'publish' cannot be introduced as an attribute.
        defaults: {
            "id": null,
            "display_name": null,
            "category": null,
            "data": null,
            "metadata" : null,
            /**
             * The Studio URL for this xblock, or null if it doesn't have one.
             */
            "studio_url": null,
            /**
             * An optional object with information about the children as well as about
             * the primary xblock type that is supported as a child.
             */
            "child_info": null,
            /**
             * An optional object with information about each of the ancestors.
             */
            "ancestor_info": null,
            /**
             * True iff:
             * 1) Edits have been made to the xblock and no published version exists.
             * 2) Edits have been made to the xblock since the last published version.
             */
            "has_changes": null,
            /**
             * True iff a published version of the xblock exists.
             */
            "published": null,
            /**
             * If true, only course staff can see the xblock regardless of publish status or
             * release date status.
             */
            "locked": null,
            /**
             * Date of the last edit to this xblock or any of its descendants.
             */
            "edited_on":null,
            /**
             * User who last edited the xblock or any of its descendants.
             */
            "edited_by":null,
            /**
             * Date of the last publish of this xblock, or null if never published.
             */
            "published_on": null,
            /**
             * User who last published the xblock, or null if never published.
             */
            "published_by": null,
            /**
             * True iff the release date of the xblock is in the past.
             */
            "released_to_students": null,
            /**
             * If the xblock is published, the date on which it will be released to students.
             * This can be null if the release date is unscheduled.
             */
            "release_date": null,
            /**
             * The xblock which is determining the release date. For instance, for a unit,
             * this will either be the parent subsection or the grandparent section.
             * This can be null if the release date is unscheduled.
             */
            "release_date_from":null
        },

        parse: function(response) {
            if (response.ancestor_info) {
                response.ancestor_info.ancestors = this.parseXBlockInfoList(response.ancestor_info.ancestors);
            }
            if (response.child_info) {
                response.child_info.children = this.parseXBlockInfoList(response.child_info.children);
            }
            return response;
        },

        parseXBlockInfoList: function(list) {
            return _.map(list, function(item) {
                return this.createChild(item);
            }, this);
        },

        createChild: function(response) {
            return new XBlockInfo(response, { parse: true });
        },

        hasChildren: function() {
            var childInfo = this.get('child_info');
            return childInfo && childInfo.children.length > 0;
        }
    });
    return XBlockInfo;
});
