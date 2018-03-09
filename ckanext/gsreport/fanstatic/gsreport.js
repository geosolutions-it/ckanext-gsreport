ckan.module('tablesorter', function($){
    var tablesorter = {
        initialize: function(){
            $.proxyAll(this, /_on/);
            $(this.el).tablesorter();
        }
    }
    return $.extend({}, tablesorter);
 });


ckan.module('autosubmit', function($){
    var autosubmit = {
        initialize: function(){
            $.proxyAll(this, /_on/);
            var that = this;
            $(this.el).change(function () {
                  document.location = $(this).val();
              });
        }
    }
    return $.extend({}, autosubmit);
 });


