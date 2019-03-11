(function(){
    $(document).ready(function () {
        $("#image-query-form").submit(function(e) {
            e.preventDefault(); // avoid to execute the actual submit of the form.

            var form = $(this);
            var url = form.attr('action');
            var data = new FormData(this);
            jQuery.each($("#image-query-form")[0][0].files, function(i, file) {
                data.append('file', file);
            });

            $.ajax({
               type: "POST",
               url: url,
               data: data,
               enctype: 'multipart/form-data',
               processData: false,
               contentType: false,
               cache: false,
               success: function(data)
               {
		   if('idx' in data) {
                     $('#disp-dist').text(data['dist']);
                     $('#disp-timestamp').text(data['timestamp']);
                     $('#disp-target').text(data['target']);
                     $('#disp-scannum').text(data['scannum']);
                     $('#disp-band').text(data['band']);
                     $('#disp-coarsechnl').text(data['coarsechnl']);
                     $('#disp-prefix').text(data['prefix']);
                     $('#disp-id').text(data['idx']);
                     $('#disp-centerfreq').text(data['centerfreq']);
                     $('#disp-img').html("<img src='" + data['wat_path'] + "' alt='waterfall'/>");
                     $('#input-error').text("");
                     $('#results').show();
		   } else {
                     $('#results').hide();
                     $('#input-error').text("Error: " + data['message']);
		   }
               },
               error: function(data) {
	       }
             });
        });
    });
})()
